import asyncio
import logging
from datetime import UTC, datetime, timedelta

import httpx

from src.config import QIITA_API_URL, QIITA_PER_PAGE, QIITA_QUERY, QIITA_TAG_QUERY
from src.models import Article, SourceDef

logger = logging.getLogger(__name__)


def _parse_qiita_item(item: dict) -> Article | None:  # type: ignore[type-arg]
    try:
        published_at_str: str = item.get("created_at", "")
        published_at: datetime | None = None
        if published_at_str:
            published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
        return Article(
            title=item["title"],
            url=item["url"],
            summary=item.get("body", "")[:300],
            source="Qiita",
            published_at=published_at,
        )
    except Exception as exc:
        logger.warning("Failed to parse Qiita item: %s", exc)
        return None


async def _fetch_qiita_query(
    client: httpx.AsyncClient, query: str, cutoff: datetime
) -> list[Article]:
    params: dict[str, str | int] = {"query": query, "per_page": QIITA_PER_PAGE}
    try:
        response = await client.get(QIITA_API_URL, params=params, timeout=15)
        response.raise_for_status()
        items: list[dict] = response.json()  # type: ignore[type-arg]
        articles = []
        for item in items:
            article = _parse_qiita_item(item)
            if article and (article.published_at is None or article.published_at >= cutoff):
                articles.append(article)
        return articles
    except Exception as exc:
        logger.warning("Failed to fetch Qiita (query=%s): %s", query, exc)
        return []


async def fetch_qiita(sources: list[SourceDef], hours: int) -> list[Article]:
    """Qiita ソース（type=="qiita"）の tag params からクエリを組み立て並列取得する。"""
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    tags = [
        s.params["tag"] for s in sources if s.type == "qiita" and s.params and "tag" in s.params
    ]

    queries = [QIITA_QUERY] + [f"{QIITA_TAG_QUERY} tag:{tag}" for tag in tags]

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[_fetch_qiita_query(client, q, cutoff) for q in queries],
            return_exceptions=True,
        )

    seen_urls: set[str] = set()
    articles: list[Article] = []
    for result in results:
        if isinstance(result, BaseException):
            logger.warning("Qiita query raised an exception: %s", result)
            continue
        for article in result:
            url_str = str(article.url)
            if url_str not in seen_urls:
                seen_urls.add(url_str)
                articles.append(article)

    logger.info("Fetched %d articles from Qiita (including tag searches)", len(articles))
    return articles
