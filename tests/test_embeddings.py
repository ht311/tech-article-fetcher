"""embedding 基盤モジュールのテスト。"""

from datetime import UTC, datetime
from typing import Literal
from unittest.mock import patch

import pytest

from src.core.models import Article
from src.services.selector.embeddings import (
    cosine_sim,
    embed_texts,
    preference_centroids,
    preference_score,
    semantic_dedup,
)


def _vec(*vals: float) -> list[float]:
    return list(vals)


def _article(title: str, *, important: bool = False, ts: datetime | None = None) -> Article:
    return Article(
        title=title,
        url=f"https://example.com/{title.replace(' ', '-')}",
        source="Test",
        is_important=important,
        published_at=ts,
    )


# ---------- cosine_sim ----------


def test_cosine_sim_identical() -> None:
    v = _vec(1.0, 0.0, 0.0)
    assert cosine_sim(v, v) == pytest.approx(1.0)


def test_cosine_sim_orthogonal() -> None:
    assert cosine_sim(_vec(1.0, 0.0), _vec(0.0, 1.0)) == pytest.approx(0.0)


def test_cosine_sim_opposite() -> None:
    assert cosine_sim(_vec(1.0, 0.0), _vec(-1.0, 0.0)) == pytest.approx(-1.0)


def test_cosine_sim_zero_vector() -> None:
    # ゼロベクトルとの類似度は 0
    assert cosine_sim(_vec(0.0, 0.0), _vec(1.0, 0.0)) == pytest.approx(0.0)


# ---------- semantic_dedup ----------


def _embs_high_sim() -> list[list[float]]:
    """2記事が高類似（コサイン ~ 1）、3記事目は別方向。"""
    return [
        _vec(1.0, 0.0, 0.0),   # article 0
        _vec(0.99, 0.14, 0.0), # article 1 ≈ 同トピック
        _vec(0.0, 1.0, 0.0),   # article 2 ≠ 別トピック
    ]


def test_semantic_dedup_clusters_similar() -> None:
    articles = [_article("A"), _article("B"), _article("C")]
    embs = _embs_high_sim()
    result = semantic_dedup(articles, embs, threshold=0.98)
    # A と B はクラスタ（sim > 0.98）→ 1 件に、C は残る
    assert len(result) == 2
    assert articles[2] in result  # C は必ず残る


def test_semantic_dedup_prefers_important() -> None:
    now = datetime.now(UTC)
    a_normal = _article("A", important=False, ts=now)
    a_important = _article("B", important=True, ts=now)
    embs = [_vec(1.0, 0.0), _vec(0.999, 0.0447)]  # 高類似
    result = semantic_dedup([a_normal, a_important], embs, threshold=0.99)
    assert len(result) == 1
    assert result[0] is a_important


def test_semantic_dedup_low_threshold_all_remain() -> None:
    articles = [_article("A"), _article("B"), _article("C")]
    embs = [_vec(1.0, 0.0), _vec(0.9, 0.1), _vec(0.0, 1.0)]
    # 閾値 1.0 以上 = 完全一致のみクラスタ化 → 全件残る
    result = semantic_dedup(articles, embs, threshold=1.0)
    assert len(result) == 3


def test_semantic_dedup_empty() -> None:
    assert semantic_dedup([], [], threshold=0.9) == []


# ---------- preference_centroids ----------


def test_preference_centroids_both() -> None:
    pairs: list[tuple[Literal["good", "bad"], list[float]]] = [
        ("good", _vec(1.0, 0.0)),
        ("good", _vec(0.0, 1.0)),
        ("bad", _vec(-1.0, 0.0)),
    ]
    good_c, bad_c = preference_centroids(pairs)
    assert good_c is not None
    assert bad_c is not None
    assert good_c == pytest.approx([0.5, 0.5])
    assert bad_c == pytest.approx([-1.0, 0.0])


def test_preference_centroids_no_bad() -> None:
    pairs: list[tuple[Literal["good", "bad"], list[float]]] = [
        ("good", _vec(1.0, 0.0)),
    ]
    good_c, bad_c = preference_centroids(pairs)
    assert good_c is not None
    assert bad_c is None


def test_preference_centroids_empty() -> None:
    good_c, bad_c = preference_centroids([])
    assert good_c is None
    assert bad_c is None


# ---------- preference_score ----------


def test_preference_score_good_only() -> None:
    good_c = _vec(1.0, 0.0)
    article_like_good = _vec(1.0, 0.0)
    score = preference_score(article_like_good, good_c, None)
    assert score == pytest.approx(1.0)


def test_preference_score_bad_only() -> None:
    bad_c = _vec(1.0, 0.0)
    article_like_bad = _vec(1.0, 0.0)
    score = preference_score(article_like_bad, None, bad_c)
    assert score == pytest.approx(-1.0)


def test_preference_score_good_beats_bad() -> None:
    good_c = _vec(1.0, 0.0)
    bad_c = _vec(0.0, 1.0)
    article = _vec(1.0, 0.0)  # good に完全一致、bad に直交
    score = preference_score(article, good_c, bad_c)
    assert score == pytest.approx(1.0)  # 1.0 - 0.0


def test_preference_score_no_centroids() -> None:
    assert preference_score(_vec(1.0, 0.0), None, None) == pytest.approx(0.0)


# ---------- embed_texts ----------


@pytest.mark.asyncio
async def test_embed_texts_no_api_key() -> None:
    with patch.dict("os.environ", {}, clear=True):
        result = await embed_texts(["hello"])
    assert result is None


@pytest.mark.asyncio
async def test_embed_texts_api_failure_returns_none() -> None:
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}):
        with patch("src.services.selector.embeddings.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.models.embed_content.side_effect = RuntimeError("API error")
            result = await embed_texts(["hello"])
    assert result is None


@pytest.mark.asyncio
async def test_embed_texts_over_limit_returns_none() -> None:
    """上限を超えるテキスト数は None を返す（ゼロコスト維持）。"""
    from src.core.config import MAX_EMBED_TEXTS_PER_RUN

    texts = ["x"] * (MAX_EMBED_TEXTS_PER_RUN + 1)
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}):
        result = await embed_texts(texts)
    assert result is None


@pytest.mark.asyncio
async def test_embed_texts_success() -> None:
    fake_emb = [0.1, 0.2, 0.3]
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}):
        with patch("src.services.selector.embeddings.genai.Client") as MockClient:
            instance = MockClient.return_value
            mock_resp = type("R", (), {"embeddings": [type("E", (), {"values": fake_emb})()]})()
            instance.models.embed_content.return_value = mock_resp
            result = await embed_texts(["hello"])
    assert result == [fake_emb]
