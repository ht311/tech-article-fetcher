from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.models import Article, SelectedArticle
from src.notifier.line_notifier import _build_message_text, send_line_message


def _make_selected(title: str = "Test Title", source: str = "Zenn", reason: str = "実用的") -> SelectedArticle:
    article = Article(
        title=title,
        url="https://example.com/article",  # type: ignore[arg-type]
        summary="Summary",
        source=source,
        published_at=datetime.now(UTC),
    )
    return SelectedArticle(article=article, reason=reason)


def test_build_message_text_contains_title() -> None:
    selected = [_make_selected("My Article", "Zenn", "実用的")]
    text = _build_message_text(selected)
    assert "My Article" in text
    assert "Zenn" in text
    assert "実用的" in text
    assert "📚" in text


def test_build_message_text_numbers_articles() -> None:
    selected = [_make_selected(f"Article {i}") for i in range(5)]
    text = _build_message_text(selected)
    for i in range(1, 6):
        assert f"{i}." in text


@pytest.mark.asyncio
async def test_send_line_message_raises_without_token() -> None:
    selected = [_make_selected()]
    with patch.dict("os.environ", {}, clear=True):
        import os

        os.environ.pop("LINE_CHANNEL_ACCESS_TOKEN", None)
        os.environ.pop("LINE_USER_ID", None)
        with pytest.raises(EnvironmentError):
            await send_line_message(selected)


@pytest.mark.asyncio
async def test_send_line_message_raises_without_user_id() -> None:
    selected = [_make_selected()]
    with patch.dict("os.environ", {"LINE_CHANNEL_ACCESS_TOKEN": "token"}):
        import os

        os.environ.pop("LINE_USER_ID", None)
        with pytest.raises(EnvironmentError):
            await send_line_message(selected)


@pytest.mark.asyncio
async def test_send_line_message_calls_api() -> None:
    selected = [_make_selected()]
    mock_api = MagicMock()
    mock_api_client = MagicMock()
    mock_api_client.__enter__ = MagicMock(return_value=mock_api_client)
    mock_api_client.__exit__ = MagicMock(return_value=False)

    with (
        patch.dict("os.environ", {"LINE_CHANNEL_ACCESS_TOKEN": "token", "LINE_USER_ID": "U123"}),
        patch("src.notifier.line_notifier.ApiClient", return_value=mock_api_client),
        patch("src.notifier.line_notifier.MessagingApi", return_value=mock_api),
    ):
        await send_line_message(selected)
        mock_api.push_message.assert_called_once()
