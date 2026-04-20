import asyncio
import json
import logging
import os
import re

from google import genai
from google.genai import types

from src.core.config import (
    GEMINI_FALLBACK_MODEL,
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
    GEMINI_RETRY_BASE_WAIT,
    SELECT_MAX_PER_CATEGORY,
)
from src.core.models import Article, CategoryDef, SelectedArticle, UserPreferences

_RETRY_AFTER_RE = re.compile(r"Please retry in ([\d.]+)s")
_DAILY_QUOTA_RE = re.compile(r"PerDay")

logger = logging.getLogger(__name__)


def _build_system_prompt(
    category: CategoryDef,
    pref_summary: str,
    max_count: int,
    include_keywords: list[str],
) -> str:
    if category.id == "others":
        topic_line = "バックエンド / フロントエンド / AWS / マネジメント以外の注目技術記事"
        category_constraint = (
            "バックエンド・フロントエンド・AWS・マネジメント系の記事は含めないこと"
        )
    else:
        topic_line = "、".join(kw.title() for kw in category.keywords if kw)
        category_constraint = f"{category.name}カテゴリに明らかに無関係な記事は含めないこと"

    base = f"""あなたはWebエンジニア向けの技術記事キュレーターです。
提供された記事リストから、{category.name}カテゴリに関連するおすすめ記事を最大{max_count}件選んでください。

優先トピック: {topic_line}

選定基準（優先順位順）:
1. 優先トピックに関連する実務で即役立つ記事
2. 話題性・新規性（リリース情報、アーキテクチャ刷新など）
3. 学習価値の高さ（深い技術解説、設計思想の説明）
4. 多様性（同一トピックの記事が重複しないよう調整）

除外基準:
- 宣伝・採用目的が主な記事
- 内容が浅い入門記事（初心者向けハンズオンなど）
- {category_constraint}

出力形式: JSON配列のみ返してください。記事がある場合は必ず1件以上選ぶこと。
[{{"index": 0, "reason": "選定理由（日本語30字以内）"}}, ...]"""

    if include_keywords:
        kw_line = "、".join(include_keywords)
        base = f"{base}\n\nユーザーが特に関心あるキーワード（含まれる記事を優先）: {kw_line}"
    if pref_summary:
        base = f"{base}\n\n{pref_summary}"
    return base


def _build_article_list_text(articles: list[Article]) -> str:
    lines = []
    for i, a in enumerate(articles):
        summary = a.summary[:100] if a.summary else ""
        lines.append(f"{i}. [{a.source}] {a.title}\n   {summary}")
    return "\n".join(lines)


def _parse_gemini_response(text: str) -> list[dict]:  # type: ignore[type-arg]
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


async def _call_gemini(
    client: genai.Client,
    model: str,
    prompt: str,
    config: types.GenerateContentConfig,
    articles: list[Article],
    max_count: int,
) -> list[SelectedArticle]:
    for attempt in range(GEMINI_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            if response.text is None:
                raise ValueError("Empty response from Gemini")
            selections = _parse_gemini_response(response.text)

            results: list[SelectedArticle] = []
            for sel in selections[:max_count]:
                idx: int = sel["index"]
                reason: str = sel["reason"]
                if 0 <= idx < len(articles):
                    results.append(SelectedArticle(article=articles[idx], reason=reason))

            logger.info("Gemini (%s) selected %d articles", model, len(results))
            return results

        except Exception as exc:
            exc_str = str(exc)

            if "429" in exc_str and _DAILY_QUOTA_RE.search(exc_str):
                logger.warning("Gemini (%s) daily quota exhausted", model)
                raise

            m = _RETRY_AFTER_RE.search(exc_str)
            wait = float(m.group(1)) + 1.0 if m else GEMINI_RETRY_BASE_WAIT * (2**attempt)
            logger.warning(
                "Gemini (%s) attempt %d/%d failed: %s (retry in %.1fs)",
                model, attempt + 1, GEMINI_MAX_RETRIES, exc, wait,
            )
            if attempt < GEMINI_MAX_RETRIES - 1:
                await asyncio.sleep(wait)

    raise RuntimeError(f"All {GEMINI_MAX_RETRIES} retries exhausted for model {model}")


def _fallback_selection(articles: list[Article], category_id: str) -> list[SelectedArticle]:
    """Gemini が 0 件返したときのフォールバック: 先頭1件を自動選定する。"""
    s = SelectedArticle(article=articles[0], reason="自動選定")
    s.category_id = category_id
    return [s]


async def _select_for_category(
    client: genai.Client,
    category: CategoryDef,
    articles: list[Article],
    pref_summary: str,
    max_count: int,
    include_keywords: list[str],
) -> tuple[str, list[SelectedArticle]]:
    if not articles:
        return (category.id, [])

    system_prompt = _build_system_prompt(category, pref_summary, max_count, include_keywords)
    cfg = types.GenerateContentConfig(system_instruction=system_prompt)
    article_text = _build_article_list_text(articles)
    prompt = (
        f"以下の記事リストから{category.name}カテゴリのおすすめを"
        f"最大{max_count}件選んでください"
        f"（必ず1件以上選ぶこと）:\n\n{article_text}"
    )

    for model in (GEMINI_MODEL, GEMINI_FALLBACK_MODEL):
        try:
            selected = await _call_gemini(client, model, prompt, cfg, articles, max_count)
            for s in selected:
                s.category_id = category.id
            if not selected:
                selected = _fallback_selection(articles, category.id)
            return (category.id, selected)
        except Exception as exc:
            logger.warning("Gemini model %s failed for category %s: %s", model, category.id, exc)

    logger.warning("All Gemini models failed for category %s; using fallback", category.id)
    return (category.id, _fallback_selection(articles, category.id))


async def select_articles_by_category(
    buckets: dict[str, list[Article]],
    category_defs: list[CategoryDef],
    preferences: UserPreferences | None = None,
    max_per_category: int = SELECT_MAX_PER_CATEGORY,
    include_keywords: list[str] | None = None,
) -> dict[str, list[SelectedArticle]]:
    """カテゴリごとに Gemini を並列呼び出しして最大 max_per_category 件を選定する。"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise OSError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    pref_summary = preferences.get_summary() if preferences else ""
    kws = include_keywords or []

    tasks = [
        _select_for_category(
            client, cat, buckets.get(cat.id, []), pref_summary, max_per_category, kws
        )
        for cat in category_defs
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    selections: dict[str, list[SelectedArticle]] = {}
    for cat, result in zip(category_defs, raw_results):
        if isinstance(result, BaseException):
            logger.warning("Category %s selection raised: %s", cat.id, result)
            selections[cat.id] = []
        else:
            _, selected = result
            selections[cat.id] = selected

    return selections
