import asyncio
import logging
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from src.core.models import Article

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; tech-article-fetcher/1.0)", "Accept": "*/*"}
_TIMEOUT = 10
_CONCURRENCY = 10


def _extract_og_image(html: str, base_url: str) -> str | None:
    soup = BeautifulSoup(html[:32768], "html.parser")
    for prop in ("og:image", "og:image:url"):
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            return urljoin(base_url, str(tag["content"]))
    tag = soup.find("meta", attrs={"name": "twitter:image"})
    if tag and tag.get("content"):
        return urljoin(base_url, str(tag["content"]))
    return None


async def _fetch_og_image(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        resp = await client.get(url, timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True)
        resp.raise_for_status()
        return _extract_og_image(resp.text, url)
    except Exception as exc:
        logger.warning("OGP fetch failed for %s: %s", url, exc)
        return None


async def enrich_thumbnails(articles: list[Article]) -> None:
    """選定記事の og:image を並列取得して thumbnail_url を上書きする。"""
    if not articles:
        return

    sem = asyncio.Semaphore(_CONCURRENCY)

    async def enrich_one(article: Article) -> None:
        async with sem:
            url = str(article.url)
            img = await _fetch_og_image(client, url)
            if img:
                article.thumbnail_url = img

    async with httpx.AsyncClient() as client:
        await asyncio.gather(*[enrich_one(a) for a in articles])
