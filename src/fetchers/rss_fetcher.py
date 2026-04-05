import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta

import feedparser
import httpx

from src.config import ARTICLE_FETCH_HOURS, RSS_SOURCES
from src.models import Article

logger = logging.getLogger(__name__)


def _parse_published(entry: feedparser.FeedParserDict) -> datetime | None:
    """feedparser のエントリから公開日時を取得する。
    published_parsed がなければ updated_parsed にフォールバック。
    """
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t is not None:
            try:
                return datetime(*t[:6], tzinfo=UTC)
            except Exception:
                continue
    return None


def _entry_to_article(entry: feedparser.FeedParserDict, source_name: str) -> Article | None:
    """feedparser のエントリを Article に変換する。URL またはタイトルが欠けていたら None を返す。"""
    url = getattr(entry, "link", None)
    title = getattr(entry, "title", None)
    if not url or not title:
        return None

    summary = getattr(entry, "summary", "") or ""
    # フィードによっては summary に HTML が含まれるため簡易的に除去する
    summary = re.sub(r"<[^>]+>", "", summary)[:300]

    published_at = _parse_published(entry)
    try:
        return Article(title=title, url=url, summary=summary, source=source_name, published_at=published_at)
    except Exception:
        return None


async def fetch_rss_source(client: httpx.AsyncClient, source: dict[str, str]) -> list[Article]:
    """単一の RSS ソースを取得して Article のリストを返す。失敗しても例外を上げず空リストを返す。"""
    name = source["name"]
    url = source["url"]
    try:
        response = await client.get(url, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        articles = [a for entry in feed.entries if (a := _entry_to_article(entry, name))]
        logger.info("Fetched %d articles from %s", len(articles), name)
        return articles
    except Exception as exc:
        # 一部ソースが落ちても他の結果に影響しないよう警告のみ
        logger.warning("Failed to fetch %s: %s", name, exc)
        return []


async def fetch_all_rss() -> list[Article]:
    """全 RSS ソースを並列取得し、直近 24 時間の記事に絞って返す。"""
    cutoff = datetime.now(UTC) - timedelta(hours=ARTICLE_FETCH_HOURS)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [fetch_rss_source(client, source) for source in RSS_SOURCES]
        results = await asyncio.gather(*tasks)

    all_articles = [a for articles in results for a in articles]

    # published_at が不明な記事は除外しない（フィードによっては日時を提供しないため）
    filtered = [a for a in all_articles if a.published_at is None or a.published_at >= cutoff]
    logger.info("RSS total: %d articles (after 24h filter: %d)", len(all_articles), len(filtered))
    return filtered
