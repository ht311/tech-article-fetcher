"""
tech-article-fetcher のエントリポイント。

処理フロー:
  1. RSS / Qiita / HN / Reddit / dev.to を並列フェッチ
  2. URL ベースで重複排除
  3. Cloudflare KV からユーザー嗜好を読み込み
  4. Gemini API で上位 5〜6 件を選定（嗜好を反映）
  5. LINE Push Message（Quick Reply ボタン付き）で送信
  6. 送信した記事リストを Cloudflare KV に書き込み
"""

import asyncio
import logging
import sys

from dotenv import load_dotenv

from src.fetchers.devto_fetcher import fetch_devto
from src.fetchers.hacker_news_fetcher import fetch_hacker_news
from src.fetchers.qiita_fetcher import fetch_qiita
from src.fetchers.reddit_fetcher import fetch_reddit
from src.fetchers.rss_fetcher import fetch_all_rss
from src.notifier.line_notifier import send_line_message
from src.selector.gemini_selector import deduplicate, select_articles
from src.storage.preferences import get_preferences, write_last_articles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    # .env ファイルがあれば環境変数に読み込む（GitHub Actions では Secrets が直接注入される）
    load_dotenv()

    logger.info("Starting tech-article-fetcher")

    # 全ソースを並列取得
    results = await asyncio.gather(
        fetch_all_rss(),
        fetch_qiita(),
        fetch_hacker_news(),
        fetch_reddit(),
        fetch_devto(),
        return_exceptions=True,
    )

    all_articles = []
    source_names = ["RSS", "Qiita", "Hacker News", "Reddit", "dev.to"]
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

    # ユーザー嗜好を読み込む（KV未設定時は空の嗜好で続行）
    preferences = await get_preferences()
    if preferences.history:
        logger.info("Loaded %d preference records", len(preferences.history))

    selected = await select_articles(unique_articles, preferences=preferences)
    logger.info("Selected %d articles", len(selected))

    await send_line_message(selected)
    logger.info("LINE message sent.")

    # 送信した記事リストを KV に保存（webhook 側がフィードバック照合に使う）
    await write_last_articles(selected)
    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
