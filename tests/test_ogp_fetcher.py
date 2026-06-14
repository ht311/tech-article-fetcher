from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.models import Article, SelectedArticle
from src.services.fetchers.ogp_fetcher import enrich_thumbnails


def _article(url: str = "https://example.com/article", thumbnail_url: str | None = None) -> Article:
    return Article(title="Test Article", url=url, source="TestSource", thumbnail_url=thumbnail_url)


def _selected(article: Article) -> SelectedArticle:
    return SelectedArticle(article=article, reason="test reason")


def _mock_response(html: str, status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.text = html
    mock_resp.status_code = status_code
    return mock_resp


OG_IMAGE_HTML = """
<html><head>
<meta property="og:image" content="https://cdn.example.com/img/og.jpg" />
</head><body></body></html>
"""

TWITTER_IMAGE_HTML = """
<html><head>
<meta name="twitter:image" content="https://cdn.example.com/img/tw.jpg" />
</head><body></body></html>
"""

NO_IMAGE_HTML = """
<html><head><title>No OGP</title></head><body></body></html>
"""

RELATIVE_IMAGE_HTML = """
<html><head>
<meta property="og:image" content="/images/og.png" />
</head><body></body></html>
"""


@pytest.mark.asyncio
async def test_enrich_sets_og_image() -> None:
    """og:image が取れた場合、thumbnail_url を上書きする。"""
    article = _article()
    assert article.thumbnail_url is None

    with patch("src.services.fetchers.ogp_fetcher.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(OG_IMAGE_HTML))

        await enrich_thumbnails([article])

    assert article.thumbnail_url == "https://cdn.example.com/img/og.jpg"


@pytest.mark.asyncio
async def test_enrich_overwrites_existing_thumbnail_with_og_image() -> None:
    """og:image を常に優先し、既存サムネを上書きする。"""
    article = _article(thumbnail_url="https://old.example.com/old.jpg")

    with patch("src.services.fetchers.ogp_fetcher.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(OG_IMAGE_HTML))

        await enrich_thumbnails([article])

    assert article.thumbnail_url == "https://cdn.example.com/img/og.jpg"


@pytest.mark.asyncio
async def test_enrich_falls_back_to_twitter_image() -> None:
    """og:image がなく twitter:image がある場合はそちらを使う。"""
    article = _article()

    with patch("src.services.fetchers.ogp_fetcher.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(TWITTER_IMAGE_HTML))

        await enrich_thumbnails([article])

    assert article.thumbnail_url == "https://cdn.example.com/img/tw.jpg"


@pytest.mark.asyncio
async def test_enrich_keeps_none_when_no_og_image() -> None:
    """og:image / twitter:image がどちらもなければ thumbnail_url は None のまま。"""
    article = _article()

    with patch("src.services.fetchers.ogp_fetcher.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(NO_IMAGE_HTML))

        await enrich_thumbnails([article])

    assert article.thumbnail_url is None


@pytest.mark.asyncio
async def test_enrich_keeps_existing_when_no_og_image() -> None:
    """og:image がなければ既存 thumbnail_url を維持する。"""
    article = _article(thumbnail_url="https://existing.example.com/img.jpg")

    with patch("src.services.fetchers.ogp_fetcher.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(NO_IMAGE_HTML))

        await enrich_thumbnails([article])

    assert article.thumbnail_url == "https://existing.example.com/img.jpg"


@pytest.mark.asyncio
async def test_enrich_resolves_relative_url() -> None:
    """og:image が相対 URL の場合、記事 URL を基準に絶対化する。"""
    article = _article(url="https://blog.example.com/posts/123")

    with patch("src.services.fetchers.ogp_fetcher.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(RELATIVE_IMAGE_HTML))

        await enrich_thumbnails([article])

    assert article.thumbnail_url == "https://blog.example.com/images/og.png"


@pytest.mark.asyncio
async def test_enrich_handles_http_error_gracefully() -> None:
    """HTTP エラーが発生しても例外を投げず、thumbnail_url はそのまま。"""
    article = _article(thumbnail_url="https://existing.example.com/img.jpg")

    with patch("src.services.fetchers.ogp_fetcher.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("Connection error"))

        await enrich_thumbnails([article])

    assert article.thumbnail_url == "https://existing.example.com/img.jpg"


@pytest.mark.asyncio
async def test_enrich_handles_empty_list() -> None:
    """空リストを渡しても例外が発生しない。"""
    await enrich_thumbnails([])  # should not raise
