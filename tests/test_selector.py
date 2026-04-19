from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.models import Article, CategoryDef
from src.services.selector.categorizer import bucket_articles, classify
from src.services.selector.gemini_selector import deduplicate, select_articles_by_category

_DEFAULT_CATS = [
    CategoryDef(
        id="backend", name="バックエンド",
        keywords=["java", "spring", "springboot", "spring boot", "postgres", "postgresql"],
        enabled=True, order=0,
    ),
    CategoryDef(
        id="frontend", name="フロントエンド",
        keywords=["react", "next.js", "nextjs", "typescript"],
        enabled=True, order=1,
    ),
    CategoryDef(
        id="aws", name="AWS",
        keywords=["aws", "amazon web services"],
        enabled=True, order=2,
    ),
    CategoryDef(
        id="management", name="マネジメント/組織",
        keywords=[
            "engineering manager", "エンジニアリングマネージャー",
            "1on1", "組織", "リーダー", "チームビルディング", "マネジメント",
        ],
        enabled=True, order=3,
    ),
    CategoryDef(id="others", name="その他", keywords=[], enabled=True, order=4),
]


def _make_article(
    url: str = "https://example.com/1",
    title: str = "Test Article",
    summary: str = "Summary",
    source: str = "TestSource",
) -> Article:
    return Article(
        title=title,
        url=url,  # type: ignore[arg-type]
        summary=summary,
        source=source,
        published_at=datetime.now(UTC),
    )


# --- deduplicate ---

def test_deduplicate_removes_duplicates() -> None:
    a1 = _make_article("https://example.com/1")
    a2 = _make_article("https://example.com/1")
    a3 = _make_article("https://example.com/2")
    assert len(deduplicate([a1, a2, a3])) == 2


def test_deduplicate_preserves_order() -> None:
    articles = [_make_article(f"https://example.com/{i}") for i in range(5)]
    result = deduplicate(articles)
    assert [str(a.url) for a in result] == [str(a.url) for a in articles]


# --- classify ---

def test_classify_backend_java() -> None:
    a = _make_article(title="Java で DDD を実践する", summary="")
    assert classify(a, _DEFAULT_CATS) == "backend"


def test_classify_backend_spring() -> None:
    a = _make_article(title="Spring Boot 3.0 のマイグレーション", summary="")
    assert classify(a, _DEFAULT_CATS) == "backend"


def test_classify_backend_postgres() -> None:
    a = _make_article(title="PostgreSQL の VACUUM", summary="")
    assert classify(a, _DEFAULT_CATS) == "backend"


def test_classify_frontend_react() -> None:
    a = _make_article(title="React 19 の新機能", summary="")
    assert classify(a, _DEFAULT_CATS) == "frontend"


def test_classify_frontend_typescript() -> None:
    a = _make_article(title="TypeScript 5.5 リリース", summary="")
    assert classify(a, _DEFAULT_CATS) == "frontend"


def test_classify_aws() -> None:
    a = _make_article(title="AWS re:Invent 2024 まとめ", summary="")
    assert classify(a, _DEFAULT_CATS) == "aws"


def test_classify_management() -> None:
    a = _make_article(title="エンジニアリングマネージャーになって1年", summary="")
    assert classify(a, _DEFAULT_CATS) == "management"


def test_classify_others() -> None:
    a = _make_article(title="Rustで書くゲームエンジン", summary="")
    assert classify(a, _DEFAULT_CATS) == "others"


def test_classify_uses_summary_when_title_has_no_keyword() -> None:
    a = _make_article(title="開発雑記", summary="spring boot でAPIを作った")
    assert classify(a, _DEFAULT_CATS) == "backend"


# --- bucket_articles ---

_MAX_INPUT = 25


def test_bucket_articles_distributes_correctly() -> None:
    articles = [
        _make_article("https://a.com/1", title="Java 入門"),
        _make_article("https://a.com/2", title="React Hooks"),
        _make_article("https://a.com/3", title="AWS Lambda の使い方"),
        _make_article("https://a.com/4", title="今週のニュース"),
    ]
    buckets = bucket_articles(articles, _DEFAULT_CATS, _MAX_INPUT)
    assert len(buckets["backend"]) == 1
    assert len(buckets["frontend"]) == 1
    assert len(buckets["aws"]) == 1
    assert len(buckets["others"]) == 1


def test_bucket_articles_truncates_to_limit() -> None:
    limit = 5
    articles = [
        _make_article(f"https://a.com/{i}", title=f"Java 記事 {i}")
        for i in range(limit + 5)
    ]
    buckets = bucket_articles(articles, _DEFAULT_CATS, limit)
    assert len(buckets["backend"]) == limit


def test_bucket_global_index_no_collision() -> None:
    articles = [_make_article(f"https://a.com/{i}") for i in range(10)]
    buckets = bucket_articles(articles, _DEFAULT_CATS, _MAX_INPUT)
    for cat_id, arts in buckets.items():
        assert len(arts) <= _MAX_INPUT, cat_id


# --- select_articles_by_category ---

@pytest.mark.asyncio
async def test_select_articles_by_category_success() -> None:
    articles = [_make_article(f"https://example.com/{i}", title=f"Java 記事 {i}") for i in range(5)]
    buckets = {"backend": articles, "frontend": [], "aws": [], "management": [], "others": []}

    mock_response = MagicMock()
    mock_response.text = '[{"index": 0, "reason": "理由1"}, {"index": 1, "reason": "理由2"}]'
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        patch("src.services.selector.gemini_selector.genai.Client", return_value=mock_client),
    ):
        selections = await select_articles_by_category(buckets, _DEFAULT_CATS)

    assert isinstance(selections, dict)
    assert len(selections["backend"]) == 2
    assert all(s.category_id == "backend" for s in selections["backend"])
    assert selections["frontend"] == []


@pytest.mark.asyncio
async def test_select_articles_by_category_raises_without_api_key() -> None:
    buckets = {"backend": [], "frontend": [], "aws": [], "management": [], "others": []}
    with patch.dict("os.environ", {}, clear=True):
        import os
        os.environ.pop("GEMINI_API_KEY", None)
        with pytest.raises(EnvironmentError):
            await select_articles_by_category(buckets, _DEFAULT_CATS)


@pytest.mark.asyncio
async def test_select_articles_by_category_empty_on_gemini_failure() -> None:
    articles = [_make_article(f"https://example.com/{i}", title=f"Java 記事 {i}") for i in range(3)]
    buckets = {"backend": articles, "frontend": [], "aws": [], "management": [], "others": []}

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API error")

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        patch("src.services.selector.gemini_selector.genai.Client", return_value=mock_client),
        patch("src.services.selector.gemini_selector.asyncio.sleep", new_callable=AsyncMock),
    ):
        selections = await select_articles_by_category(buckets, _DEFAULT_CATS)

    assert selections["backend"] == []
