from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import (
    GEMINI_FALLBACK_MODEL,
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
    default_category_defs,
)
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


# --- classify: 境界マッチ + config デフォルトキーワード（plan-18） ---

def _config_cats() -> list[CategoryDef]:
    """config.py のデフォルトカテゴリ定義（キーワード拡充の検証用）。"""
    return [CategoryDef.model_validate(c) for c in default_category_defs()]


def test_classify_no_false_positive_short_ascii() -> None:
    """短い略語キーワードが英単語の一部に誤爆しない（ecs/rds/rust）。"""
    cats = _config_cats()
    assert classify(_make_article(title="Writing better specs", summary=""), cats) == "others"
    assert classify(_make_article(title="5000 words essay", summary=""), cats) == "others"
    assert classify(_make_article(title="Zero Trust Architecture", summary=""), cats) == "others"


def test_classify_ascii_keyword_adjacent_to_japanese() -> None:
    """空白なしで日本語に直結する ASCII キーワードもマッチする。"""
    a = _make_article(title="Lambdaで作るサーバーレスAPI", summary="")
    assert classify(a, _config_cats()) == "aws"


def test_classify_aws_services() -> None:
    cats = _config_cats()
    assert classify(_make_article(title="DynamoDB のインデックス設計", summary=""), cats) == "aws"
    assert classify(_make_article(title="ECS Fargate 移行のポイント", summary=""), cats) == "aws"


def test_classify_frontend_expanded() -> None:
    cats = _config_cats()
    assert classify(_make_article(title="Vue 3 の Composition API", summary=""), cats) == "frontend"
    assert classify(_make_article(title="CSS Grid レイアウト実践", summary=""), cats) == "frontend"


def test_classify_javascript_no_longer_matches_java() -> None:
    """javascript が backend の "java" に誤爆せず frontend に分類される。"""
    a = _make_article(title="JavaScript の非同期処理", summary="")
    assert classify(a, _config_cats()) == "frontend"


def test_classify_management_expanded() -> None:
    cats = _config_cats()
    assert classify(_make_article(title="スクラムイベントの改善", summary=""), cats) == "management"
    assert classify(_make_article(title="テックリードの役割とは", summary=""), cats) == "management"


def test_classify_japanese_keywords_still_substring() -> None:
    """日本語キーワードは従来通り部分一致で動く。"""
    a = _make_article(title="組織づくりの話", summary="")
    assert classify(a, _config_cats()) == "management"


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


def test_bucket_articles_preference_rerank_promotes_high_score() -> None:
    """url_to_score が渡されると、スコア高い記事が切り詰め後も残る。"""
    limit = 2
    articles = [
        _make_article(f"https://a.com/{i}", title=f"Java 記事 {i}")
        for i in range(5)
    ]
    # 末尾の記事（index=4）に最高スコアを与え、切り詰め後に残ることを確認
    url_to_score = {str(a.url): float(i) for i, a in enumerate(articles)}
    buckets = bucket_articles(articles, _DEFAULT_CATS, limit, url_to_score=url_to_score)
    surviving_urls = {str(a.url) for a in buckets["backend"]}
    assert "https://a.com/4" in surviving_urls  # 最高スコアは残る
    assert "https://a.com/0" not in surviving_urls  # 最低スコアは落とされる


def test_bucket_articles_url_to_score_none_uses_published_at() -> None:
    """url_to_score=None のとき従来の published_at 降順で動作する（後方互換）。"""
    from datetime import timedelta
    now = datetime.now(UTC)
    articles = [
        _make_article(f"https://a.com/{i}", title=f"Java 記事 {i}")
        for i in range(3)
    ]
    articles[0] = Article(
        title="Java 記事 0", url="https://a.com/0",
        source="Test", published_at=now - timedelta(hours=2),
    )
    articles[1] = Article(
        title="Java 記事 1", url="https://a.com/1",
        source="Test", published_at=now - timedelta(hours=1),
    )
    articles[2] = Article(
        title="Java 記事 2", url="https://a.com/2",
        source="Test", published_at=now,
    )
    buckets = bucket_articles(articles, _DEFAULT_CATS, 2)
    # 最新の2件が残る
    surviving_urls = {str(a.url) for a in buckets["backend"]}
    assert "https://a.com/2" in surviving_urls
    assert "https://a.com/1" in surviving_urls
    assert "https://a.com/0" not in surviving_urls


# --- select_articles_by_category ---

@pytest.mark.asyncio
async def test_select_articles_by_category_success() -> None:
    articles = [_make_article(f"https://example.com/{i}", title=f"Java 記事 {i}") for i in range(5)]
    buckets = {"backend": articles, "frontend": [], "aws": [], "management": [], "others": []}

    mock_response = MagicMock()
    mock_response.text = (
        '[{"index": 0, "reason": "理由1", "summary": "要約1"},'
        ' {"index": 1, "reason": "理由2", "summary": "要約2"}]'
    )
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
    assert selections["backend"][0].summary == "要約1"
    assert selections["backend"][1].summary == "要約2"


@pytest.mark.asyncio
async def test_select_articles_by_category_summary_missing_graceful() -> None:
    """Gemini が summary を返さなくてもエラーにならず空文字になる。"""
    articles = [_make_article("https://example.com/0", title="Java 記事")]
    buckets = {"backend": articles, "frontend": [], "aws": [], "management": [], "others": []}

    mock_response = MagicMock()
    mock_response.text = '[{"index": 0, "reason": "理由のみ"}]'
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        patch("src.services.selector.gemini_selector.genai.Client", return_value=mock_client),
    ):
        selections = await select_articles_by_category(buckets, _DEFAULT_CATS)

    assert selections["backend"][0].summary == ""


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

    assert len(selections["backend"]) == 1
    assert selections["backend"][0].article == articles[0]
    assert selections["backend"][0].reason == "自動選定"


# --- フォールバックモデル（plan-18） ---

def test_fallback_model_differs_from_primary() -> None:
    """フォールバックがプライマリと同一だとクォータ枯渇時の劣化パスが no-op になる。"""
    assert GEMINI_MODEL != GEMINI_FALLBACK_MODEL


@pytest.mark.asyncio
async def test_daily_quota_switches_to_fallback_model() -> None:
    """日次クォータ枯渇（429 + PerDay）でプライマリを即中断しフォールバックへ切り替える。"""
    articles = [_make_article("https://example.com/0", title="Java 記事")]
    buckets = {"backend": articles, "frontend": [], "aws": [], "management": [], "others": []}

    mock_response = MagicMock()
    mock_response.text = '[{"index": 0, "reason": "理由", "summary": "要約"}]'
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        Exception(
            "429 RESOURCE_EXHAUSTED: Quota exceeded for metric "
            "GenerateRequestsPerDayPerProjectPerModel"
        ),
        mock_response,
    ]

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        patch("src.services.selector.gemini_selector.genai.Client", return_value=mock_client),
        patch("src.services.selector.gemini_selector.asyncio.sleep", new_callable=AsyncMock),
    ):
        selections = await select_articles_by_category(buckets, _DEFAULT_CATS)

    calls = mock_client.models.generate_content.call_args_list
    assert len(calls) == 2  # プライマリ1回 + フォールバック1回（リトライを浪費しない）
    assert calls[1].kwargs["model"] == GEMINI_FALLBACK_MODEL
    assert selections["backend"][0].summary == "要約"


@pytest.mark.asyncio
async def test_model_loop_skips_duplicate_model() -> None:
    """フォールバックがプライマリと同一値に退行しても同じモデルを2周しない。"""
    articles = [_make_article("https://example.com/0", title="Java 記事")]
    buckets = {"backend": articles, "frontend": [], "aws": [], "management": [], "others": []}

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API error")

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        patch("src.services.selector.gemini_selector.genai.Client", return_value=mock_client),
        patch("src.services.selector.gemini_selector.asyncio.sleep", new_callable=AsyncMock),
        patch("src.services.selector.gemini_selector.GEMINI_FALLBACK_MODEL", GEMINI_MODEL),
    ):
        await select_articles_by_category(buckets, _DEFAULT_CATS)

    assert mock_client.models.generate_content.call_count == GEMINI_MAX_RETRIES
