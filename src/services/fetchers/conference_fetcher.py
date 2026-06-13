"""カンファレンス名リストから SpeakerDeck / Docswell のスライドを収集するフェッチャー。

SpeakerDeck も Docswell も検索用の公開 Atom フィードがないため HTML をパースする。
HTML 構造変更時はログ警告＋空リストで graceful degradation する。
"""

import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from src.core.models import Article, Conference

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; tech-article-fetcher/1.0)", "Accept": "*/*"}

_SD_SEARCH_URL = "https://speakerdeck.com/search?q={query}"
_DW_SEARCH_URL = "https://www.docswell.com/search?key={query}"

# ISO8601 / "N days ago" などを正規化するための簡易パターン
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _parse_iso_date(text: str) -> datetime | None:
    m = _ISO_DATE_RE.search(text)
    if not m:
        return None
    try:
        return datetime.fromisoformat(m.group()).replace(tzinfo=UTC)
    except ValueError:
        return None


def _parse_speakerdeck_html(html: str, source_label: str) -> list[Article]:
    """SpeakerDeck 検索結果 HTML からスライドを抽出する。"""
    articles = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        # 各スライドは <div class="speakerdeck-talk"> か <article> で囲まれている
        cards = soup.select("div.speakerdeck-talk, article.speakerdeck-talk")
        if not cards:
            # 構造が変わった可能性 — 別セレクタを試みる
            cards = soup.select("li.talk")
        for card in cards:
            a_tag = card.find("a", href=re.compile(r"/[^/]+/[^/]+"))
            if not a_tag:
                continue
            raw_href = a_tag.get("href", "")
            href = str(raw_href) if raw_href else ""
            if not href.startswith("http"):
                href = f"https://speakerdeck.com{href}"
            title = a_tag.get_text(strip=True) or card.get_text(strip=True)[:80]

            # 日付: <time datetime="..."> があれば使う
            time_tag = card.find("time")
            published_at: datetime | None = None
            if time_tag:
                raw_dt = time_tag.get("datetime", "") or time_tag.get_text(strip=True)
                published_at = _parse_iso_date(str(raw_dt))

            try:
                articles.append(Article(
                    title=title,
                    url=href,  # type: ignore[arg-type]
                    source=source_label,
                    published_at=published_at,
                    is_important=True,
                ))
            except Exception:
                continue
    except Exception as exc:
        logger.warning("Failed to parse SpeakerDeck HTML: %s", exc)
    return articles


def _parse_docswell_html(html: str, source_label: str) -> list[Article]:
    """Docswell 検索結果 HTML からスライドを抽出する。"""
    articles = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        # 各スライドカード: <div class="slide-card"> や <article> など
        cards = soup.select("div.slide-card, article.slide-card, li.slide-item")
        if not cards:
            cards = soup.select("div[class*='slide']")
        for card in cards:
            a_tag = card.find("a", href=re.compile(r"/slides/"))
            if not a_tag:
                continue
            raw_href = a_tag.get("href", "")
            href = str(raw_href) if raw_href else ""
            if not href.startswith("http"):
                href = f"https://www.docswell.com{href}"
            title_tag = card.find(["h2", "h3", "h4"]) or a_tag
            title = title_tag.get_text(strip=True)[:120] if title_tag else ""
            if not title:
                continue

            time_tag = card.find("time")
            published_at = None
            if time_tag:
                raw_dt = time_tag.get("datetime", "") or time_tag.get_text(strip=True)
                published_at = _parse_iso_date(str(raw_dt))

            try:
                articles.append(Article(
                    title=title,
                    url=href,  # type: ignore[arg-type]
                    source=source_label,
                    published_at=published_at,
                    is_important=True,
                ))
            except Exception:
                continue
    except Exception as exc:
        logger.warning("Failed to parse Docswell HTML: %s", exc)
    return articles


async def _fetch_speakerdeck(client: httpx.AsyncClient, conf: Conference) -> list[Article]:
    url = _SD_SEARCH_URL.format(query=quote_plus(conf.name))
    try:
        resp = await client.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        articles = _parse_speakerdeck_html(resp.text, f"SpeakerDeck:{conf.name}")
        logger.info("SpeakerDeck[%s]: %d slides", conf.name, len(articles))
        return articles
    except Exception as exc:
        logger.warning("Failed to fetch SpeakerDeck for %s: %s", conf.name, exc)
        return []


async def _fetch_docswell(client: httpx.AsyncClient, conf: Conference) -> list[Article]:
    url = _DW_SEARCH_URL.format(query=quote_plus(conf.name))
    try:
        resp = await client.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        articles = _parse_docswell_html(resp.text, f"Docswell:{conf.name}")
        logger.info("Docswell[%s]: %d slides", conf.name, len(articles))
        return articles
    except Exception as exc:
        logger.warning("Failed to fetch Docswell for %s: %s", conf.name, exc)
        return []


async def fetch_conference_slides(
    conferences: list[Conference],
    hours: int,
) -> list[Article]:
    """カンファレンス名リストから SpeakerDeck + Docswell のスライドを並列取得する。"""
    if not conferences:
        return []

    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = []
        for conf in conferences:
            tasks.append(_fetch_speakerdeck(client, conf))
            tasks.append(_fetch_docswell(client, conf))
        results = await asyncio.gather(*tasks, return_exceptions=True)

    seen_urls: set[str] = set()
    articles: list[Article] = []
    for result in results:
        if isinstance(result, BaseException):
            logger.warning("Conference fetcher raised exception: %s", result)
            continue
        for article in result:
            # published_at 不明のスライドは期間フィルタをパス（カンファ直後はよく不明）
            if article.published_at and article.published_at < cutoff:
                continue
            url_str = str(article.url)
            if url_str in seen_urls:
                continue
            seen_urls.add(url_str)
            articles.append(article)

    logger.info("Fetched %d conference slides total", len(articles))
    return articles
