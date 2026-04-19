import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta

import feedparser
import httpx

from src.models import Article, SourceDef

logger = logging.getLogger(__name__)


def _parse_published(entry: feedparser.FeedParserDict) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t is not None:
            try:
                return datetime(t[0], t[1], t[2], t[3], t[4], t[5], tzinfo=UTC)
            except Exception:
                continue
    return None


def _extract_thumbnail(entry: feedparser.FeedParserDict) -> str | None:
    thumbnails = getattr(entry, "media_thumbnail", None)
    if thumbnails and isinstance(thumbnails, list) and thumbnails[0].get("url"):
        return str(thumbnails[0]["url"])
    media_contents = getattr(entry, "media_content", None)
    if media_contents and isinstance(media_contents, list):
        for mc in media_contents:
            if mc.get("url") and mc.get("medium") == "image":
                return str(mc["url"])
    enclosures = getattr(entry, "enclosures", None)
    if enclosures and isinstance(enclosures, list):
        for enc in enclosures:
            if enc.get("url") and str(enc.get("type", "")).startswith("image/"):
                return str(enc["url"])
    return None


def _entry_to_article(entry: feedparser.FeedParserDict, source_name: str) -> Article | None:
    url = getattr(entry, "link", None)
    title = getattr(entry, "title", None)
    if not url or not title:
        return None

    summary = getattr(entry, "summary", "") or ""
    summary = re.sub(r"<[^>]+>", "", summary)[:300]

    published_at = _parse_published(entry)
    thumbnail_url = _extract_thumbnail(entry)
    try:
        return Article(
            title=title,
            url=url,
            summary=summary,
            source=source_name,
            published_at=published_at,
            thumbnail_url=thumbnail_url,
        )
    except Exception:
        return None


async def fetch_rss_source(client: httpx.AsyncClient, source: SourceDef) -> list[Article]:
    try:
        response = await client.get(source.url or "", timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        articles = [a for entry in feed.entries if (a := _entry_to_article(entry, source.name))]
        logger.info("Fetched %d articles from %s", len(articles), source.name)
        return articles
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", source.name, exc)
        return []


async def fetch_all_rss(sources: list[SourceDef], hours: int) -> list[Article]:
    """RSS ソース（type=="rss"）を並列取得し、指定時間以内の記事を返す。"""
    rss_sources = [s for s in sources if s.type == "rss"]
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [fetch_rss_source(client, source) for source in rss_sources]
        results = await asyncio.gather(*tasks)

    all_articles = [a for articles in results for a in articles]
    filtered = [a for a in all_articles if a.published_at is None or a.published_at >= cutoff]
    logger.info(
        "RSS total: %d articles (after %dh filter: %d)", len(all_articles), hours, len(filtered)
    )
    return filtered
