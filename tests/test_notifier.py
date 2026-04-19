from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.models import Article, SelectedArticle
from src.notifier.line_notifier import _build_category_flex_message, send_category_messages


def _make_selected(
    title: str = "Test Title",
    source: str = "Zenn",
    reason: str = "実用的",
    cat_id: str = "backend",
) -> SelectedArticle:
    article = Article(
        title=title,
        url="https://example.com/article",  # type: ignore[arg-type]
        summary="Summary",
        source=source,
        published_at=datetime.now(UTC),
    )
    return SelectedArticle(article=article, reason=reason, category_id=cat_id)


# --- _build_category_flex_message ---

def test_build_category_flex_message_has_category_name() -> None:
    selected = [_make_selected("Java 記事")]
    msg = _build_category_flex_message("バックエンド", selected, global_offset=0)
    assert "バックエンド" in msg.alt_text


def test_build_category_flex_message_article_count_in_alt() -> None:
    selected = [_make_selected(f"Article {i}") for i in range(3)]
    msg = _build_category_flex_message("フロントエンド", selected, global_offset=5)
    assert "3 件" in msg.alt_text


def test_build_category_flex_message_caps_at_5() -> None:
    selected = [_make_selected(f"Article {i}") for i in range(7)]
    msg = _build_category_flex_message("その他", selected, global_offset=0)
    assert "5 件" in msg.alt_text


# --- send_category_messages ---

@pytest.mark.asyncio
async def test_send_category_messages_raises_without_token() -> None:
    selections = {"backend": [_make_selected()], "frontend": [], "aws": [], "management": [], "others": []}
    with patch.dict("os.environ", {}, clear=True):
        import os
        os.environ.pop("LINE_CHANNEL_ACCESS_TOKEN", None)
        os.environ.pop("LINE_USER_ID", None)
        with pytest.raises(EnvironmentError):
            await send_category_messages(selections)


@pytest.mark.asyncio
async def test_send_category_messages_raises_without_user_id() -> None:
    selections = {"backend": [_make_selected()], "frontend": [], "aws": [], "management": [], "others": []}
    with patch.dict("os.environ", {"LINE_CHANNEL_ACCESS_TOKEN": "token"}):
        import os
        os.environ.pop("LINE_USER_ID", None)
        with pytest.raises(EnvironmentError):
            await send_category_messages(selections)


@pytest.mark.asyncio
async def test_send_category_messages_skips_empty_categories() -> None:
    selections = {
        "backend": [_make_selected("Java 記事")],
        "frontend": [],
        "aws": [],
        "management": [],
        "others": [],
    }

    mock_api = MagicMock()
    mock_api_client = MagicMock()
    mock_api_client.__enter__ = MagicMock(return_value=mock_api_client)
    mock_api_client.__exit__ = MagicMock(return_value=False)

    with (
        patch.dict("os.environ", {"LINE_CHANNEL_ACCESS_TOKEN": "token", "LINE_USER_ID": "U123"}),
        patch("src.notifier.line_notifier.ApiClient", return_value=mock_api_client),
        patch("src.notifier.line_notifier.MessagingApi", return_value=mock_api),
    ):
        await send_category_messages(selections)

    assert mock_api.push_message.call_count == 1


@pytest.mark.asyncio
async def test_send_category_messages_sends_in_order() -> None:
    selections = {
        "backend": [_make_selected("Java 記事", cat_id="backend")],
        "frontend": [_make_selected("React 記事", cat_id="frontend")],
        "aws": [],
        "management": [],
        "others": [],
    }

    mock_api = MagicMock()
    mock_api_client = MagicMock()
    mock_api_client.__enter__ = MagicMock(return_value=mock_api_client)
    mock_api_client.__exit__ = MagicMock(return_value=False)

    with (
        patch.dict("os.environ", {"LINE_CHANNEL_ACCESS_TOKEN": "token", "LINE_USER_ID": "U123"}),
        patch("src.notifier.line_notifier.ApiClient", return_value=mock_api_client),
        patch("src.notifier.line_notifier.MessagingApi", return_value=mock_api),
    ):
        await send_category_messages(selections)

    assert mock_api.push_message.call_count == 2
