"""
tech-article-fetcher のエントリポイント。

処理フロー:
  1. KV から UserSettings を読み込み RuntimeConfig を構築
  2. RSS / Qiita / SpeakerDeck を並列フェッチ（RuntimeConfig のソース定義を使用）
  3. URL ベースで重複排除
  4. カテゴリごとにバケット分け（RuntimeConfig のカテゴリ定義を使用）
  5. KV からユーザー嗜好を読み込み
  6. カテゴリごとに Gemini API で選定（並列呼び出し）
  7. カテゴリ別に LINE Push Message を逐次送信
  8. 送信した記事リストを Cloudflare KV に書き込み
"""

import asyncio
import logging
import sys
from datetime import UTC, datetime

from dotenv import load_dotenv

from src.fetchers.qiita_fetcher import fetch_qiita
from src.fetchers.rss_fetcher import fetch_all_rss
from src.fetchers.speakerdeck_fetcher import fetch_speakerdeck
from src.models import Article
from src.notifier.line_notifier import send_category_messages
from src.runtime_config import build_runtime_config
from src.selector.categorizer import bucket_articles
from src.selector.gemini_selector import deduplicate, select_articles_by_category
from src.storage.preferences import (
    get_preferences,
    get_settings,
    write_article_history,
    write_last_articles,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    load_dotenv()

    logger.info("Starting tech-article-fetcher")

    settings = await get_settings()
    rc = build_runtime_config(settings)
    logger.info(
        "RuntimeConfig: %d sources, %d categories, fetch_hours=%d",
        len(rc.sources),
        len(rc.category_defs),
        rc.article_fetch_hours,
    )

    results = await asyncio.gather(
        fetch_all_rss(rc.sources, rc.article_fetch_hours),
        fetch_qiita(rc.sources, rc.article_fetch_hours),
        fetch_speakerdeck(rc.sources, rc.article_fetch_hours),
        return_exceptions=True,
    )

    all_articles: list[Article] = []
    source_names = ["RSS", "Qiita", "SpeakerDeck"]
    for name, result in zip(source_names, results):
        if isinstance(result, BaseException):
            logger.warning("Source %s raised an exception: %s", name, result)
        else:
            all_articles.extend(result)

    logger.info("Total fetched: %d articles", len(all_articles))

    unique_articles = deduplicate(all_articles)
    logger.info("After deduplication: %d articles", len(unique_articles))

    if not unique_articles:
        logger.error("No articles fetched. Exiting.")
        sys.exit(1)

    # exclude_keywords フィルタ
    lower_excludes = [kw.lower() for kw in rc.exclude_keywords]
    if lower_excludes:
        unique_articles = [
            a for a in unique_articles
            if not any(
                kw in a.title.lower() or kw in a.summary.lower()
                for kw in lower_excludes
            )
        ]

    buckets = bucket_articles(unique_articles, rc.category_defs, rc.gemini_max_input_per_category)
    for cat_id, arts in buckets.items():
        logger.info("Bucket %s: %d articles", cat_id, len(arts))

    preferences = await get_preferences()
    if preferences.history:
        logger.info("Loaded %d preference records", len(preferences.history))

    selections = await select_articles_by_category(
        buckets,
        category_defs=rc.category_defs,
        preferences=preferences,
        max_per_category=rc.max_per_category,
        include_keywords=rc.include_keywords,
    )
    total = sum(len(v) for v in selections.values())
    logger.info("Selected total %d articles across %d categories", total, len(selections))

    await send_category_messages(selections, rc.category_defs)
    logger.info("LINE messages sent.")

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    await asyncio.gather(
        write_last_articles(selections),
        write_article_history(today, selections),
    )
    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
