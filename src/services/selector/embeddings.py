"""Gemini embedding 基盤。意味的重複排除と嗜好ベクトル再ランクに使う共通モジュール。"""

import logging
import math
import os
from datetime import UTC, datetime
from typing import Literal

from google import genai

from src.core.config import GEMINI_EMBED_MODEL, MAX_EMBED_TEXTS_PER_RUN
from src.core.models import Article

logger = logging.getLogger(__name__)

_EPOCH = datetime.min.replace(tzinfo=UTC)


async def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Gemini embedding をバッチ取得する。

    API キー未設定・テキスト数が MAX_EMBED_TEXTS_PER_RUN 超・API 失敗時はすべて None を返す。
    呼び出し側は None をフォールバック（現状ロジック継続）のトリガーとして扱う。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    if len(texts) > MAX_EMBED_TEXTS_PER_RUN:
        logger.warning(
            "embed_texts: %d texts exceed MAX_EMBED_TEXTS_PER_RUN=%d; skipping embedding",
            len(texts),
            MAX_EMBED_TEXTS_PER_RUN,
        )
        return None

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.embed_content(
            model=GEMINI_EMBED_MODEL,
            contents=texts,
        )
        return [list(e.values) for e in response.embeddings]  # type: ignore[union-attr,arg-type]
    except Exception as exc:
        logger.warning("embed_texts failed: %s; falling back", exc)
        return None


def cosine_sim(a: list[float], b: list[float]) -> float:
    """2ベクトル間のコサイン類似度を返す。ゼロベクトルとの類似度は 0。"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _cluster_priority(article: Article) -> tuple[int, datetime]:
    """クラスタ内で残す記事の優先度キー（降順）: is_important > published_at 新しい順。"""
    return (
        1 if article.is_important else 0,
        article.published_at if article.published_at else _EPOCH,
    )


def semantic_dedup(
    articles: list[Article],
    embeddings: list[list[float]],
    threshold: float,
) -> list[Article]:
    """コサイン類似度 >= threshold の記事をクラスタ化し、各クラスタから 1 件だけ残す。

    残す優先度: is_important > published_at が新しい > 元の順序（先着）。
    """
    n = len(articles)
    if n == 0:
        return []

    assigned: list[int | None] = [None] * n  # クラスタ代表インデックス

    for i in range(n):
        if assigned[i] is not None:
            continue
        assigned[i] = i
        for j in range(i + 1, n):
            if assigned[j] is not None:
                continue
            if cosine_sim(embeddings[i], embeddings[j]) >= threshold:
                assigned[j] = i  # i のクラスタに吸収

    clusters: dict[int, list[int]] = {}
    for idx, rep in enumerate(assigned):
        assert rep is not None
        clusters.setdefault(rep, []).append(idx)

    result: list[Article] = []
    for members in clusters.values():
        best = max(members, key=lambda idx: _cluster_priority(articles[idx]))
        result.append(articles[best])

    return result


def preference_centroids(
    feedback_embeddings: list[tuple[Literal["good", "bad"], list[float]]],
) -> tuple[list[float] | None, list[float] | None]:
    """good・bad それぞれの重心ベクトルを返す。対応する履歴が無い側は None。"""
    good_vecs = [emb for action, emb in feedback_embeddings if action == "good"]
    bad_vecs = [emb for action, emb in feedback_embeddings if action == "bad"]

    def _mean(vecs: list[list[float]]) -> list[float] | None:
        if not vecs:
            return None
        dim = len(vecs[0])
        return [sum(v[d] for v in vecs) / len(vecs) for d in range(dim)]

    return _mean(good_vecs), _mean(bad_vecs)


def preference_score(
    article_emb: list[float],
    good_centroid: list[float] | None,
    bad_centroid: list[float] | None,
) -> float:
    """sim(article, good重心) - sim(article, bad重心) を返す。重心が無い側は 0 として扱う。"""
    good_sim = cosine_sim(article_emb, good_centroid) if good_centroid is not None else 0.0
    bad_sim = cosine_sim(article_emb, bad_centroid) if bad_centroid is not None else 0.0
    return good_sim - bad_sim
