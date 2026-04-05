import logging
from datetime import UTC, datetime, timedelta

import httpx

from src.config import ARTICLE_FETCH_HOURS, DEVTO_API_URL, DEVTO_PER_PAGE, DEVTO_TOP_PERIOD
from src.models import Article

logger = logging.getLogger(__name__)


def _parse_devto_article(item: dict) -> Article | None:  # type: ignore[type-arg]
    """dev.to API レスポンスを Article に変換する。"""
    try:
        url = item.get("url", "")
        title = item.get("title", "")
        if not url or not title:
            return None

        published_at: datetime | None = None
        published_str = item.get("published_at", "")
        if published_str:
            published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))

        description = item.get("description", "") or ""

        return Article(
            title=title,
            url=url,
            summary=description[:300],
            source="dev.to",
            published_at=published_at,
        )
    except Exception as exc:
        logger.debug("Failed to parse dev.to article: %s", exc)
        return None


async def fetch_devto() -> list[Article]:
    """dev.to のトレンド記事を取得し、直近 24 時間でフィルタして返す。
    失敗しても例外を上げず空リストを返す。
    """
    cutoff = datetime.now(UTC) - timedelta(hours=ARTICLE_FETCH_HOURS)
    params = {"top": DEVTO_TOP_PERIOD, "per_page": DEVTO_PER_PAGE}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(DEVTO_API_URL, params=params, timeout=15)
            response.raise_for_status()
            items: list[dict] = response.json()  # type: ignore[type-arg]

        articles = []
        for item in items:
            article = _parse_devto_article(item)
            if article and (article.published_at is None or article.published_at >= cutoff):
                articles.append(article)

        logger.info("Fetched %d articles from dev.to", len(articles))
        return articles
    except Exception as exc:
        logger.warning("Failed to fetch dev.to: %s", exc)
        return []
