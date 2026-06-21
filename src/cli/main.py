"""
tech-article-fetcher のエントリポイント。

処理フロー:
  1. KV から UserSettings を読み込み RuntimeConfig を構築
  2. RSS / Qiita / SpeakerDeck を並列フェッチ（通常24h）
     重要ソース（important=True）は延長ウィンドウ（EXTENDED_FETCH_HOURS）で取得
  3. KV からカンファレンスリストを読み込み、スライドを並列フェッチ
  4. URL ベースで重複排除 → 送信済みURL（直近N日）を除外
  5. カテゴリごとにバケット分け
  6. KV からユーザー嗜好を読み込み
  7. カテゴリごとに Gemini API で選定（並列呼び出し）
  8. 重要記事のピン留め（Gemini が落とした重要記事をカテゴリ先頭へ強制挿入）
  9. カテゴリ別に LINE Push Message を逐次送信
  10. 送信記事リストを Cloudflare KV に書き込み
"""

import asyncio
import logging
import sys
from datetime import UTC, datetime

from dotenv import load_dotenv

from src.core.clock import jst_today
from src.core.config import (
    CONFERENCE_SEARCH_HOURS,
    ENABLE_PREFERENCE_RERANK,
    ENABLE_SEMANTIC_DEDUP,
    EXTENDED_FETCH_HOURS,
    MAX_PINNED_PER_CATEGORY,
    SEMANTIC_DEDUP_THRESHOLD,
    SENT_HISTORY_DEDUP_DAYS,
)
from src.core.models import Article, CategoryDef, SelectedArticle
from src.core.runtime_config import build_default_user_settings, build_runtime_config
from src.services.fetchers.conference_fetcher import fetch_conference_slides
from src.services.fetchers.ogp_fetcher import enrich_thumbnails
from src.services.fetchers.qiita_fetcher import fetch_qiita
from src.services.fetchers.rss_fetcher import fetch_all_rss
from src.services.fetchers.speakerdeck_fetcher import fetch_speakerdeck
from src.services.notifier.line_notifier import send_category_messages
from src.services.selector.categorizer import bucket_articles
from src.services.selector.embeddings import (
    embed_texts,
    preference_centroids,
    preference_score,
    semantic_dedup,
)
from src.services.selector.gemini_selector import deduplicate, select_articles_by_category
from src.services.storage.preferences import (
    get_conferences,
    get_preferences,
    get_recent_sent_urls,
    get_settings,
    write_article_history,
    write_default_settings,
    write_last_articles,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _pin_important(
    selections: dict[str, list[SelectedArticle]],
    buckets: dict[str, list[Article]],
    category_defs: list[CategoryDef],
    max_pins: int,
) -> dict[str, list[SelectedArticle]]:
    """Gemini が選ばなかった重要記事をカテゴリ先頭へピン留めする。"""
    for cat in category_defs:
        selected_urls = {str(s.article.url) for s in selections.get(cat.id, [])}
        candidates = [
            a for a in buckets.get(cat.id, [])
            if a.is_important and str(a.url) not in selected_urls
        ]
        # published_at 新しい順に最大 max_pins 件ピン
        _epoch = datetime.min.replace(tzinfo=UTC)
        candidates.sort(key=lambda a: a.published_at or _epoch, reverse=True)
        pins = [
            SelectedArticle(
                article=a,
                reason=f"重要: {a.source}",
                summary=a.summary[:100] if a.summary else "",
                category_id=cat.id,
            )
            for a in candidates[:max_pins]
        ]
        if pins:
            logger.info("Pinned %d important articles to category %s", len(pins), cat.id)
            selections[cat.id] = pins + selections.get(cat.id, [])
    return selections


async def main() -> None:
    load_dotenv()

    logger.info("Starting tech-article-fetcher")

    await write_default_settings(build_default_user_settings())

    settings = await get_settings()
    rc = build_runtime_config(settings)
    logger.info(
        "RuntimeConfig: %d sources, %d categories, fetch_hours=%d",
        len(rc.sources),
        len(rc.category_defs),
        rc.article_fetch_hours,
    )

    # 通常ソースと重要ソースを分離してフェッチ時間を変える
    normal_sources = [s for s in rc.sources if not s.important]
    important_sources = [s for s in rc.sources if s.important]

    conferences, sent_urls = await asyncio.gather(
        get_conferences(),
        get_recent_sent_urls(SENT_HISTORY_DEDUP_DAYS),
    )
    logger.info(
        "Conferences: %d, sent URLs for dedup: %d",
        len(conferences.conferences),
        len(sent_urls),
    )

    fetch_tasks = [
        fetch_all_rss(normal_sources, rc.article_fetch_hours),
        fetch_all_rss(important_sources, EXTENDED_FETCH_HOURS),
        fetch_qiita(rc.sources, EXTENDED_FETCH_HOURS),
        fetch_speakerdeck(rc.sources, rc.article_fetch_hours),
        fetch_conference_slides(conferences.conferences, CONFERENCE_SEARCH_HOURS),
    ]
    results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    all_articles: list[Article] = []
    source_names = ["RSS(normal)", "RSS(important)", "Qiita", "SpeakerDeck", "Conference"]
    for name, result in zip(source_names, results):
        if isinstance(result, BaseException):
            logger.warning("Source %s raised an exception: %s", name, result)
        else:
            logger.info("Source %s: %d articles", name, len(result))
            all_articles.extend(result)

    logger.info("Total fetched: %d articles", len(all_articles))

    unique_articles = deduplicate(all_articles)
    logger.info("After deduplication: %d articles", len(unique_articles))

    # 送信済み記事を除外（延長ウィンドウによる再送防止）
    if sent_urls:
        before = len(unique_articles)
        unique_articles = [a for a in unique_articles if str(a.url) not in sent_urls]
        logger.info("Filtered %d already-sent articles", before - len(unique_articles))

    if not unique_articles:
        logger.error("No articles fetched. Exiting.")
        sys.exit(1)

    lower_excludes = [kw.lower() for kw in rc.exclude_keywords]
    if lower_excludes:
        unique_articles = [
            a for a in unique_articles
            if not any(
                kw in a.title.lower() or kw in a.summary.lower()
                for kw in lower_excludes
            )
        ]

    # embedding 取得（意味的 dedup・嗜好再ランクの共通基盤。失敗時は None でフォールバック）
    preferences = await get_preferences()
    if preferences.history:
        logger.info("Loaded %d preference records", len(preferences.history))

    article_embeddings: list[list[float]] | None = None
    url_to_score: dict[str, float] | None = None

    if ENABLE_SEMANTIC_DEDUP or ENABLE_PREFERENCE_RERANK:
        article_titles = [a.title for a in unique_articles]
        feedback_titles = [f.title for f in preferences.history]
        all_texts = article_titles + feedback_titles
        all_embeddings = await embed_texts(all_texts)

        if all_embeddings is not None:
            # URL -> embedding のマップで管理（dedup 後も追跡できるようにする）
            url_to_emb: dict[str, list[float]] = {
                str(a.url): emb
                for a, emb in zip(unique_articles, all_embeddings[: len(unique_articles)])
            }
            feedback_embeddings_raw = all_embeddings[len(unique_articles):]

            if ENABLE_SEMANTIC_DEDUP:
                article_embeddings = all_embeddings[: len(unique_articles)]
                before = len(unique_articles)
                unique_articles = semantic_dedup(
                    unique_articles, article_embeddings, SEMANTIC_DEDUP_THRESHOLD
                )
                logger.info(
                    "After semantic dedup: %d articles (removed %d)",
                    len(unique_articles),
                    before - len(unique_articles),
                )

            if ENABLE_PREFERENCE_RERANK and preferences.history:
                feedback_pairs = list(zip(
                    [f.action for f in preferences.history],
                    feedback_embeddings_raw,
                ))
                good_c, bad_c = preference_centroids(feedback_pairs)
                if good_c is not None or bad_c is not None:
                    url_to_score = {
                        url: preference_score(emb, good_c, bad_c)
                        for url, emb in url_to_emb.items()
                        if url in {str(a.url) for a in unique_articles}
                    }
                    logger.info(
                        "Preference reranking enabled (good=%s, bad=%s)",
                        good_c is not None, bad_c is not None,
                    )
        else:
            logger.info("Embedding unavailable; using fallback (URL dedup + published_at order)")

    buckets = bucket_articles(
        unique_articles, rc.category_defs, rc.gemini_max_input_per_category, url_to_score
    )
    for cat_id, arts in buckets.items():
        logger.info("Bucket %s: %d articles", cat_id, len(arts))

    selections = await select_articles_by_category(
        buckets,
        category_defs=rc.category_defs,
        preferences=preferences,
        max_per_category=rc.max_per_category,
        include_keywords=rc.include_keywords,
    )

    # 重要記事のピン留め
    selections = _pin_important(selections, buckets, rc.category_defs, MAX_PINNED_PER_CATEGORY)

    total = sum(len(v) for v in selections.values())
    logger.info("Selected total %d articles across %d categories", total, len(selections))

    # 選定記事の og:image を取得して thumbnail_url を補完/上書き
    selected_articles = [s.article for arts in selections.values() for s in arts]
    await enrich_thumbnails(selected_articles)
    logger.info("Thumbnail enrichment done.")

    await send_category_messages(selections, rc.category_defs)
    logger.info("LINE messages sent.")

    today = jst_today()
    await asyncio.gather(
        write_last_articles(selections, rc.category_defs),
        write_article_history(today, selections, rc.category_defs),
    )
    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
