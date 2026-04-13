"""SpeakerDeck から日本語スライドを取得するフェッチャー。

公式 API なし。カテゴリ Atom フィード (/c/<category>.atom) を利用:
  - 各カテゴリフィードは最新 18 件を返す
  - CJK 文字 (U+3000–U+9FFF) がタイトルまたはサマリーに含まれるものを「日本語」と判定

/trending.atom / /popular.atom はエントリが空のため利用不可。
"""

import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta

import feedparser
import httpx

from src.config import ARTICLE_FETCH_HOURS, SPEAKERDECK_CATEGORIES
from src.models import Article

logger = logging.getLogger(__name__)

SPEAKERDECK_CATEGORY_ATOM = "https://speakerdeck.com/c/{category}.atom"

_CJK_RE = re.compile(r"[\u3000-\u9fff\uff00-\uffef]")
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; tech-article-fetcher/1.0)", "Accept": "*/*"}


def _is_japanese(text: str) -> bool:
    return bool(_CJK_RE.search(text))


def _parse_entry(entry: feedparser.FeedParserDict) -> Article | None:
    url = getattr(entry, "link", None)
    title = getattr(entry, "title", None)
    if not url or not title:
        return None

    summary = getattr(entry, "summary", "") or ""
    summary = re.sub(r"<[^>]+>", "", summary)[:300]

    published_at: datetime | None = None
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                published_at = datetime(*t[:6], tzinfo=UTC)
                break
            except Exception:
                continue

    thumbnail_url: str | None = None
    thumbnails = getattr(entry, "media_thumbnail", None)
    if thumbnails and isinstance(thumbnails, list) and thumbnails[0].get("url"):
        thumbnail_url = thumbnails[0]["url"]

    try:
        return Article(
            title=title,
            url=url,
            summary=summary,
            source="SpeakerDeck",
            published_at=published_at,
            thumbnail_url=thumbnail_url,
        )
    except Exception:
        return None


async def _fetch_category(client: httpx.AsyncClient, category: str) -> list[Article]:
    url = SPEAKERDECK_CATEGORY_ATOM.format(category=category)
    try:
        response = await client.get(url, headers=_HEADERS, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        articles = []
        for entry in feed.entries:
            article = _parse_entry(entry)
            if article and _is_japanese(article.title + article.summary):
                articles.append(article)
        logger.info("SpeakerDeck /c/%s: %d entries, %d Japanese", category, len(feed.entries), len(articles))
        return articles
    except Exception as exc:
        logger.warning("Failed to fetch SpeakerDeck /c/%s: %s", category, exc)
        return []


async def fetch_speakerdeck() -> list[Article]:
    """SpeakerDeck カテゴリフィードから日本語スライドを並列取得して返す。"""
    cutoff = datetime.now(UTC) - timedelta(hours=ARTICLE_FETCH_HOURS)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        results = await asyncio.gather(
            *[_fetch_category(client, cat) for cat in SPEAKERDECK_CATEGORIES],
            return_exceptions=True,
        )

    seen_urls: set[str] = set()
    articles: list[Article] = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning("SpeakerDeck category raised exception: %s", result)
            continue
        for article in result:
            if article.published_at and article.published_at < cutoff:
                continue
            url_str = str(article.url)
            if url_str in seen_urls:
                continue
            seen_urls.add(url_str)
            articles.append(article)

    logger.info("Fetched %d Japanese slides from SpeakerDeck", len(articles))
    return articles
