import logging
from datetime import UTC, datetime, timedelta

import httpx

from src.config import ARTICLE_FETCH_HOURS, QIITA_API_URL, QIITA_PER_PAGE, QIITA_QUERY
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


async def fetch_qiita() -> list[Article]:
    """Qiita API からストック数 50 以上の記事を取得し、直近 24 時間に絞って返す。
    失敗しても例外を上げず空リストを返す。
    """
    cutoff = datetime.now(UTC) - timedelta(hours=ARTICLE_FETCH_HOURS)
    params = {"query": QIITA_QUERY, "per_page": QIITA_PER_PAGE}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(QIITA_API_URL, params=params, timeout=15)
            response.raise_for_status()
            items: list[dict] = response.json()  # type: ignore[type-arg]

        articles = []
        for item in items:
            article = _parse_qiita_item(item)
            if article and (article.published_at is None or article.published_at >= cutoff):
                articles.append(article)

        logger.info("Fetched %d articles from Qiita", len(articles))
        return articles
    except Exception as exc:
        logger.warning("Failed to fetch Qiita: %s", exc)
        return []
