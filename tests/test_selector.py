from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models import Article, SelectedArticle
from src.selector.gemini_selector import deduplicate, select_articles


def _make_article(url: str = "https://example.com/1", source: str = "TestSource") -> Article:
    return Article(
        title="Test Article",
        url=url,  # type: ignore[arg-type]
        summary="Summary",
        source=source,
        published_at=datetime.now(UTC),
    )


def _success_response_text() -> str:
    return (
        '[{"index": 0, "reason": "理由1"}, {"index": 1, "reason": "理由2"}, '
        '{"index": 2, "reason": "理由3"}, {"index": 3, "reason": "理由4"}, '
        '{"index": 4, "reason": "理由5"}]'
    )


def test_deduplicate_removes_duplicates() -> None:
    a1 = _make_article("https://example.com/1")
    a2 = _make_article("https://example.com/1")  # duplicate
    a3 = _make_article("https://example.com/2")
    result = deduplicate([a1, a2, a3])
    assert len(result) == 2


def test_deduplicate_preserves_order() -> None:
    articles = [_make_article(f"https://example.com/{i}") for i in range(5)]
    result = deduplicate(articles)
    assert [str(a.url) for a in result] == [str(a.url) for a in articles]


@pytest.mark.asyncio
async def test_select_articles_success() -> None:
    articles = [_make_article(f"https://example.com/{i}") for i in range(10)]

    mock_response = MagicMock()
    mock_response.text = _success_response_text()

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        patch("src.selector.gemini_selector.genai.Client", return_value=mock_client),
    ):
        selected = await select_articles(articles)
        assert len(selected) == 5
        assert all(isinstance(s, SelectedArticle) for s in selected)


@pytest.mark.asyncio
async def test_select_articles_raises_without_api_key() -> None:
    articles = [_make_article()]
    with patch.dict("os.environ", {}, clear=True):
        import os

        os.environ.pop("GEMINI_API_KEY", None)
        with pytest.raises(EnvironmentError):
            await select_articles(articles)


@pytest.mark.asyncio
async def test_select_articles_retries_on_failure() -> None:
    articles = [_make_article(f"https://example.com/{i}") for i in range(10)]

    call_count = 0
    success_response = MagicMock()
    success_response.text = _success_response_text()

    def mock_generate(**kwargs: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("Transient error")
        return success_response

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = mock_generate

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        patch("src.selector.gemini_selector.genai.Client", return_value=mock_client),
        patch("src.selector.gemini_selector.asyncio.sleep", new_callable=AsyncMock),
    ):
        selected = await select_articles(articles)
        assert len(selected) == 5
        assert call_count == 2
