import asyncio
import logging
from datetime import UTC, datetime, timedelta

import httpx

from src.config import ARTICLE_FETCH_HOURS, QIITA_API_URL, QIITA_PER_PAGE, QIITA_QUERY, QIITA_TAG_QUERY, QIITA_TAGS
from src.models import Article

logger = logging.getLogger(__name__)


def _parse_qiita_item(item: dict) -> Article | None:  # type: ignore[type-arg]
    """Qiita API のレスポンスアイテムを Article に変換する。"""
    try:
        published_at_str: str = item.get("created_at", "")
        published_at: datetime | None = None
        if published_at_str:
            # Qiita は ISO 8601 形式で返すが末尾が "Z" の場合があるため変換
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


async def _fetch_qiita_query(client: httpx.AsyncClient, query: str, cutoff: datetime) -> list[Article]:
    """指定クエリで Qiita API を呼び出し、cutoff 以降の記事を返す。"""
    params = {"query": query, "per_page": QIITA_PER_PAGE}
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


async def fetch_qiita() -> list[Article]:
    """Qiita API から人気記事＋トピックタグ別記事を並列取得し、重複排除して返す。"""
    cutoff = datetime.now(UTC) - timedelta(hours=ARTICLE_FETCH_HOURS)

    queries = [QIITA_QUERY] + [f"{QIITA_TAG_QUERY} tag:{tag}" for tag in QIITA_TAGS]

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[_fetch_qiita_query(client, q, cutoff) for q in queries],
            return_exceptions=True,
        )

    seen_urls: set[str] = set()
    articles: list[Article] = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Qiita query raised an exception: %s", result)
            continue
        for article in result:
            url_str = str(article.url)
            if url_str not in seen_urls:
                seen_urls.add(url_str)
                articles.append(article)

    logger.info("Fetched %d articles from Qiita (including tag searches)", len(articles))
    return articles
