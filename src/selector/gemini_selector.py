import asyncio
import json
import logging
import os
import re

from google import genai
from google.genai import types

from src.config import GEMINI_MAX_RETRIES, GEMINI_MODEL, GEMINI_RETRY_BASE_WAIT, SELECT_MAX, SELECT_MIN
from src.models import Article, SelectedArticle

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


async def select_articles(articles: list[Article]) -> list[SelectedArticle]:
    """Gemini API を使って記事リストから上位 5〜7 件を選定する。
    失敗時は指数バックオフで最大 GEMINI_MAX_RETRIES 回リトライする。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)

    article_text = _build_article_list_text(articles)
    prompt = f"以下の記事リストから5〜7件選んでください:\n\n{article_text}"

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
                raise
    return []  # unreachable
