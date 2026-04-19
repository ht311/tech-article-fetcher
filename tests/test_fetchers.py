from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.fetchers.qiita_fetcher import fetch_qiita
from src.fetchers.rss_fetcher import _entry_to_article, _parse_published, fetch_all_rss
from src.models import SourceDef


def _rss_source(name: str = "TestSource", url: str = "https://example.com/feed") -> SourceDef:
    return SourceDef(name=name, type="rss", url=url, enabled=True)


def _qiita_source(tag: str = "Java") -> SourceDef:
    return SourceDef(name=f"Qiita:{tag}", type="qiita", params={"tag": tag}, enabled=True)


# --- rss_fetcher ---


def _make_entry(**kwargs):  # type: ignore[no-untyped-def]
    entry = MagicMock()
    entry.link = kwargs.get("link", "https://example.com/article")
    entry.title = kwargs.get("title", "Test Article")
    entry.summary = kwargs.get("summary", "Summary text")
    entry.published_parsed = kwargs.get("published_parsed", None)
    entry.updated_parsed = kwargs.get("updated_parsed", None)
    return entry


def test_parse_published_returns_none_when_missing() -> None:
    entry = _make_entry()
    assert _parse_published(entry) is None


def test_parse_published_returns_datetime() -> None:
    import time

    t = time.gmtime(0)
    entry = _make_entry(published_parsed=t)
    result = _parse_published(entry)
    assert result is not None
    assert result.tzinfo is not None


def test_entry_to_article_success() -> None:
    entry = _make_entry()
    article = _entry_to_article(entry, "TestSource")
    assert article is not None
    assert article.source == "TestSource"
    assert article.title == "Test Article"


def test_entry_to_article_missing_url() -> None:
    entry = _make_entry(link=None)
    article = _entry_to_article(entry, "TestSource")
    assert article is None


def test_entry_to_article_missing_title() -> None:
    entry = _make_entry(title=None)
    article = _entry_to_article(entry, "TestSource")
    assert article is None


@pytest.mark.asyncio
async def test_fetch_all_rss_handles_errors() -> None:
    sources = [_rss_source()]
    with patch("src.fetchers.rss_fetcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get.side_effect = Exception("Network error")

        articles = await fetch_all_rss(sources, hours=24)
        assert isinstance(articles, list)


@pytest.mark.asyncio
async def test_fetch_all_rss_skips_non_rss_sources() -> None:
    sources = [
        SourceDef(name="Qiita:Java", type="qiita", params={"tag": "Java"}, enabled=True),
    ]
    with patch("src.fetchers.rss_fetcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        articles = await fetch_all_rss(sources, hours=24)
        assert articles == []
        mock_client.get.assert_not_called()


# --- qiita_fetcher ---


def _make_qiita_item(
    title: str = "Qiita Article", url: str = "https://qiita.com/items/abc"
) -> dict:  # type: ignore[type-arg]
    return {
        "title": title,
        "url": url,
        "body": "body text",
        "created_at": datetime.now(UTC).isoformat(),
    }


@pytest.mark.asyncio
async def test_fetch_qiita_returns_articles() -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [_make_qiita_item()]

    with patch("src.fetchers.qiita_fetcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get.return_value = mock_response

        articles = await fetch_qiita([_qiita_source("Java")], hours=24)
        assert len(articles) == 1
        assert articles[0].source == "Qiita"


@pytest.mark.asyncio
async def test_fetch_qiita_handles_error() -> None:
    with patch("src.fetchers.qiita_fetcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get.side_effect = Exception("API error")

        articles = await fetch_qiita([_qiita_source()], hours=24)
        assert articles == []


@pytest.mark.asyncio
async def test_fetch_qiita_no_sources_returns_articles() -> None:
    """Qiita ソースがない場合でも一般クエリ分は実行される。"""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = []

    with patch("src.fetchers.qiita_fetcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get.return_value = mock_response

        articles = await fetch_qiita([], hours=24)
        assert articles == []
