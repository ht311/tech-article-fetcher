import asyncio
import logging
from datetime import UTC, datetime, timedelta

import httpx

from src.config import ARTICLE_FETCH_HOURS, REDDIT_BASE_URL, REDDIT_MIN_SCORE, REDDIT_PER_PAGE, REDDIT_SUBREDDITS
from src.models import Article

logger = logging.getLogger(__name__)

# Reddit は User-Agent を設定しないと 429 が返る
_USER_AGENT = "tech-article-fetcher/1.0"


async def _fetch_subreddit(client: httpx.AsyncClient, subreddit: str) -> list[Article]:
    """サブレditのホット投稿を取得して Article のリストを返す。"""
    url = REDDIT_BASE_URL.format(subreddit=subreddit)
    try:
        response = await client.get(url, params={"limit": REDDIT_PER_PAGE}, timeout=15)
        response.raise_for_status()
        data: dict = response.json()  # type: ignore[type-arg]
        posts = data.get("data", {}).get("children", [])

        articles = []
        for post in posts:
            article = _parse_post(post.get("data", {}), subreddit)
            if article:
                articles.append(article)

        logger.info("Fetched %d articles from r/%s", len(articles), subreddit)
        return articles
    except Exception as exc:
        logger.warning("Failed to fetch r/%s: %s", subreddit, exc)
        return []


def _parse_post(post: dict, subreddit: str) -> Article | None:  # type: ignore[type-arg]
    """Reddit 投稿データを Article に変換する。"""
    try:
        # self-post（テキストのみ）・スコア不足は除外
        if post.get("is_self", True):
            return None
        if post.get("score", 0) < REDDIT_MIN_SCORE:
            return None

        url = post.get("url", "")
        title = post.get("title", "")
        if not url or not title:
            return None

        published_at: datetime | None = None
        ts = post.get("created_utc")
        if ts:
            published_at = datetime.fromtimestamp(float(ts), tz=UTC)

        return Article(
            title=title,
            url=url,
            summary="",
            source=f"Reddit r/{subreddit}",
            published_at=published_at,
        )
    except Exception as exc:
        logger.debug("Failed to parse Reddit post: %s", exc)
        return None


async def fetch_reddit() -> list[Article]:
    """複数サブレditのホット投稿を並列取得し、直近 24 時間でフィルタして返す。
    失敗しても例外を上げず空リストを返す。
    """
    cutoff = datetime.now(UTC) - timedelta(hours=ARTICLE_FETCH_HOURS)
    try:
        headers = {"User-Agent": _USER_AGENT}
        async with httpx.AsyncClient(headers=headers) as client:
            tasks = [_fetch_subreddit(client, sub) for sub in REDDIT_SUBREDDITS]
            results = await asyncio.gather(*tasks)

        all_articles = [a for articles in results for a in articles]
        filtered = [
            a for a in all_articles
            if a.published_at is None or a.published_at >= cutoff
        ]
        logger.info("Reddit total: %d articles (after 24h filter: %d)", len(all_articles), len(filtered))
        return filtered
    except Exception as exc:
        logger.warning("Failed to fetch Reddit: %s", exc)
        return []
