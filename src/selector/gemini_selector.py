import asyncio
import json
import logging
import os
import re

from google import genai
from google.genai import types

from src.config import GEMINI_MAX_RETRIES, GEMINI_MODEL, GEMINI_RETRY_BASE_WAIT, SELECT_MAX, SELECT_MIN
from src.models import Article, SelectedArticle, UserPreferences

_RETRY_AFTER_RE = re.compile(r"Please retry in ([\d.]+)s")

logger = logging.getLogger(__name__)

# Gemini に渡すシステムプロンプト。選定基準・除外基準・出力形式を定義する。
SYSTEM_PROMPT = """あなたはWebエンジニア向けの技術記事キュレーターです。
提供された記事リストから、以下の基準でおすすめ記事を5〜7件選んでください。

選定基準（優先順位順）:
1. 実務で即役立つ技術トピック（新機能、ベストプラクティス、パフォーマンス改善）
2. 話題性・新規性（リリース情報、アーキテクチャ刷新など）
3. 学習価値の高さ（深い技術解説、設計思想の説明）
4. 多様性（同一トピックの記事が重複しないよう調整）

除外基準:
- 宣伝・採用目的が主な記事
- 内容が浅い入門記事（初心者向けハンズオンなど）

出力形式: JSON配列のみ返してください。
[{"index": 0, "reason": "選定理由（日本語30字以内）"}, ...]"""


def _build_article_list_text(articles: list[Article]) -> str:
    """記事リストを Gemini に渡せるテキスト形式に変換する。"""
    lines = []
    for i, a in enumerate(articles):
        summary = a.summary[:100] if a.summary else ""
        lines.append(f"{i}. [{a.source}] {a.title}\n   {summary}")
    return "\n".join(lines)


def _parse_gemini_response(text: str) -> list[dict]:  # type: ignore[type-arg]
    """Gemini のレスポンステキストから JSON 配列を抽出する。
    余分な説明文が混入しても正規表現で JSON 部分だけを取り出す。
    """
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if not match:
        raise ValueError("JSON array not found in Gemini response")
    return json.loads(match.group())  # type: ignore[no-any-return]


def deduplicate(articles: list[Article]) -> list[Article]:
    """URL が重複する記事を除去する（先着優先・順序を保持）。"""
    seen_urls: set[str] = set()
    unique: list[Article] = []
    for a in articles:
        url_str = str(a.url)
        if url_str not in seen_urls:
            seen_urls.add(url_str)
            unique.append(a)
    return unique


async def select_articles(
    articles: list[Article],
    preferences: UserPreferences | None = None,
) -> list[SelectedArticle]:
    """Gemini API を使って記事リストから上位 5〜6 件を選定する。
    preferences が指定されている場合はユーザー嗜好をプロンプトに追記する。
    失敗時は指数バックオフで最大 GEMINI_MAX_RETRIES 回リトライする。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)

    # 嗜好サマリーをシステムプロンプトに追記する
    system_prompt = SYSTEM_PROMPT
    if preferences:
        summary = preferences.get_summary()
        if summary:
            system_prompt = f"{SYSTEM_PROMPT}\n\n{summary}"

    config = types.GenerateContentConfig(system_instruction=system_prompt)

    article_text = _build_article_list_text(articles)
    prompt = f"以下の記事リストから5〜6件選んでください:\n\n{article_text}"

    for attempt in range(GEMINI_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config,
            )
            selections = _parse_gemini_response(response.text)

            results: list[SelectedArticle] = []
            for sel in selections[:SELECT_MAX]:
                idx: int = sel["index"]
                reason: str = sel["reason"]
                if 0 <= idx < len(articles):
                    results.append(SelectedArticle(article=articles[idx], reason=reason))

            if len(results) < SELECT_MIN:
                raise ValueError(f"Too few articles selected: {len(results)}")

            logger.info("Gemini selected %d articles", len(results))
            return results

        except Exception as exc:
            exc_str = str(exc)
            # 429 でリトライ時間が指定されている場合はそれを使う
            m = _RETRY_AFTER_RE.search(exc_str)
            if m:
                wait = float(m.group(1)) + 1.0
            else:
                wait = GEMINI_RETRY_BASE_WAIT * (2**attempt)
            logger.warning(
                "Gemini attempt %d/%d failed: %s (retry in %.1fs)",
                attempt + 1,
                GEMINI_MAX_RETRIES,
                exc,
                wait,
            )
            if attempt < GEMINI_MAX_RETRIES - 1:
                await asyncio.sleep(wait)
            else:
                logger.warning("All Gemini retries exhausted; falling back to recency-based selection")
                return _fallback_select(articles)
    return []  # unreachable


def _fallback_select(articles: list[Article]) -> list[SelectedArticle]:
    """Gemini が利用できないときに直近の記事から上位 SELECT_MAX 件を返すフォールバック。
    published_at が新しい順にソートし、ソースが分散するよう調整する。
    """
    from datetime import datetime, timezone

    epoch = datetime.min.replace(tzinfo=timezone.utc)
    sorted_articles = sorted(
        articles,
        key=lambda a: a.published_at if a.published_at else epoch,
        reverse=True,
    )
    seen_sources: set[str] = set()
    selected: list[SelectedArticle] = []
    # まずソースが重複しない記事を優先的に選ぶ
    for article in sorted_articles:
        if article.source not in seen_sources:
            seen_sources.add(article.source)
            selected.append(SelectedArticle(article=article, reason="最新記事（フォールバック選定）"))
        if len(selected) >= SELECT_MAX:
            break
    # それでも足りなければ残りから補充
    if len(selected) < SELECT_MIN:
        for article in sorted_articles:
            if article not in [s.article for s in selected]:
                selected.append(SelectedArticle(article=article, reason="最新記事（フォールバック選定）"))
            if len(selected) >= SELECT_MAX:
                break
    logger.info("Fallback selected %d articles", len(selected))
    return selected
