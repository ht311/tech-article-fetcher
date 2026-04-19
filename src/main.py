"""
tech-article-fetcher のエントリポイント。

処理フロー:
  1. RSS（日本語ブログ・企業ブログ・海外公式ブログ）/ Qiita / SpeakerDeck を並列フェッチ
  2. URL ベースで重複排除
  3. 大カテゴリ（バックエンド / フロントエンド / AWS / マネジメント・組織 / その他）ごとにバケット分け
  4. Cloudflare KV からユーザー嗜好を読み込み
  5. カテゴリごとに Gemini API で最大 5 件を選定（並列呼び出し）
  6. カテゴリ別に LINE Push Message を逐次送信
  7. 送信した記事リストを Cloudflare KV に書き込み
"""

import asyncio
import logging
import sys
from datetime import UTC, datetime

from dotenv import load_dotenv

from src.fetchers.qiita_fetcher import fetch_qiita
from src.fetchers.rss_fetcher import fetch_all_rss
from src.fetchers.speakerdeck_fetcher import fetch_speakerdeck
from src.notifier.line_notifier import send_category_messages
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

    results = await asyncio.gather(
        fetch_all_rss(),
        fetch_qiita(),
        fetch_speakerdeck(),
        return_exceptions=True,
    )

    all_articles = []
    source_names = ["RSS", "Qiita", "SpeakerDeck"]
    for name, result in zip(source_names, results):
        if isinstance(result, Exception):
            logger.warning("Source %s raised an exception: %s", name, result)
        else:
            all_articles.extend(result)

    logger.info("Total fetched: %d articles", len(all_articles))

    unique_articles = deduplicate(all_articles)
    logger.info("After deduplication: %d articles", len(unique_articles))

    if not unique_articles:
        logger.error("No articles fetched. Exiting.")
        sys.exit(1)

    buckets = bucket_articles(unique_articles)
    for cat_id, arts in buckets.items():
        logger.info("Bucket %s: %d articles", cat_id, len(arts))

    preferences, settings = await asyncio.gather(get_preferences(), get_settings())
    if preferences.history:
        logger.info("Loaded %d preference records", len(preferences.history))

    # settings に基づきバケットをフィルタ
    lower_excludes = [kw.lower() for kw in settings.exclude_keywords]
    for cat_id in list(buckets.keys()):
        if not settings.categories.get(cat_id, True):
            buckets[cat_id] = []
            continue
        arts = buckets[cat_id]
        if settings.sources_enabled:
            arts = [a for a in arts if settings.sources_enabled.get(a.source, True)]
        if lower_excludes:
            arts = [
                a for a in arts
                if not any(
                    kw in a.title.lower() or kw in a.summary.lower()
                    for kw in lower_excludes
                )
            ]
        buckets[cat_id] = arts

    selections = await select_articles_by_category(
        buckets,
        preferences=preferences,
        max_per_category=settings.max_per_category,
        include_keywords=settings.include_keywords,
    )
    total = sum(len(v) for v in selections.values())
    logger.info("Selected total %d articles across %d categories", total, len(selections))

    await send_category_messages(selections)
    logger.info("LINE messages sent.")

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    await asyncio.gather(
        write_last_articles(selections),
        write_article_history(today, selections),
    )
    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
