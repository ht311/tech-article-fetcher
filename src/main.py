"""
tech-article-fetcher のエントリポイント。

処理フロー:
  1. RSS フィード（14 ソース）と Qiita API を並列フェッチ
  2. URL ベースで重複排除
  3. Gemini API で上位 5〜7 件を選定
  4. LINE Push Message で送信
"""

import asyncio
import logging
import sys

from dotenv import load_dotenv

from src.fetchers.qiita_fetcher import fetch_qiita
from src.fetchers.rss_fetcher import fetch_all_rss
from src.notifier.line_notifier import send_line_message
from src.selector.gemini_selector import deduplicate, select_articles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    # .env ファイルがあれば環境変数に読み込む（GitHub Actions では Secrets が直接注入される）
    load_dotenv()

    logger.info("Starting tech-article-fetcher")

    # RSS と Qiita を同時に取得して時間を節約する
    rss_articles, qiita_articles = await asyncio.gather(fetch_all_rss(), fetch_qiita())
    all_articles = rss_articles + qiita_articles
    logger.info("Total fetched: %d articles", len(all_articles))

    unique_articles = deduplicate(all_articles)
    logger.info("After deduplication: %d articles", len(unique_articles))

    if not unique_articles:
        logger.error("No articles fetched. Exiting.")
        sys.exit(1)

    selected = await select_articles(unique_articles)
    logger.info("Selected %d articles", len(selected))

    await send_line_message(selected)
    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
