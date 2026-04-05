import asyncio
import logging
from datetime import UTC, datetime, timedelta

import httpx

from src.config import ARTICLE_FETCH_HOURS, HN_FETCH_COUNT, HN_ITEM_URL, HN_MIN_SCORE, HN_TOP_STORIES_URL
from src.models import Article

logger = logging.getLogger(__name__)


async def _fetch_item(client: httpx.AsyncClient, item_id: int) -> Article | None:
    """HN の個別アイテムを取得して Article に変換する。"""
    try:
        url = HN_ITEM_URL.format(id=item_id)
        response = await client.get(url, timeout=10)
        response.raise_for_status()
        item: dict = response.json()  # type: ignore[type-arg]

        # story 以外（job, comment など）・URL なし・スコア不足は除外
        if item.get("type") != "story":
            return None
        article_url = item.get("url")
        if not article_url:
            return None
        if item.get("score", 0) < HN_MIN_SCORE:
            return None

        title = item.get("title", "")
        if not title:
            return None

        published_at: datetime | None = None
        ts = item.get("time")
        if ts:
            published_at = datetime.fromtimestamp(ts, tz=UTC)

        return Article(
            title=title,
            url=article_url,
            summary="",
            source="Hacker News",
            published_at=published_at,
        )
    except Exception as exc:
        logger.debug("Failed to fetch HN item %d: %s", item_id, exc)
        return None


async def fetch_hacker_news() -> list[Article]:
    """Hacker News のトップストーリーを取得し、直近 24 時間・スコア閾値でフィルタして返す。
    失敗しても例外を上げず空リストを返す。
    """
    cutoff = datetime.now(UTC) - timedelta(hours=ARTICLE_FETCH_HOURS)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(HN_TOP_STORIES_URL, timeout=15)
            response.raise_for_status()
            story_ids: list[int] = response.json()

            # 上位 HN_FETCH_COUNT 件を並列取得
            tasks = [_fetch_item(client, sid) for sid in story_ids[:HN_FETCH_COUNT]]
            results = await asyncio.gather(*tasks)

        articles = [
            a for a in results
            if a is not None and (a.published_at is None or a.published_at >= cutoff)
        ]
        logger.info("Fetched %d articles from Hacker News", len(articles))
        return articles
    except Exception as exc:
        logger.warning("Failed to fetch Hacker News: %s", exc)
        return []
