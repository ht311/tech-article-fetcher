"""週次カンファレンス発見ジョブ。

Gemini の Google 検索グラウンディングで直近・今後3ヶ月の日本の主要技術カンファレンス名を
取得し、Cloudflare KV の `conferences` リストへ append-only で追記する。

実行方法:
  python -m src.cli.update_conferences
"""

import asyncio
import json
import logging
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.core.config import GEMINI_MODEL
from src.services.storage.preferences import get_conferences, merge_conferences, write_conferences

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_PROMPT = """
あなたは日本の技術カンファレンス情報に詳しいエージェントです。
Google 検索を使い、直近3ヶ月以内に開催された、または今後3ヶ月以内に開催予定の
日本の主要な技術カンファレンス名（エンジニア向け）を列挙してください。

条件:
- 日本国内で開催されるもの（またはオンライン開催で日本語コンテンツが中心のもの）
- 技術系エンジニア向け（Java, Web, クラウド, インフラ, フロントエンド, アジャイル等）
- 規模が大きい・認知度が高いもの（小規模な勉強会は除く）

出力形式: JSON 配列のみ返してください。
["カンファレンス名1", "カンファレンス名2", ...]

カンファレンス名は SpeakerDeck や Docswell で検索に使えるシンプルな名称にしてください。
例: ["JJUG CCC", "JAWS DAYS", "TSKaigi", "DeveloperSummit", "CloudNative Days"]
"""

_JSON_RE = re.compile(r"\[.*?\]", re.DOTALL)


def _parse_names(text: str) -> list[str]:
    m = _JSON_RE.search(text)
    if not m:
        logger.warning("Could not find JSON array in Gemini response")
        return []
    try:
        names = json.loads(m.group())
        return [n for n in names if isinstance(n, str) and n.strip()]
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse Gemini response as JSON: %s", exc)
        return []


async def discover_conferences() -> list[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise OSError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=_PROMPT,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        text = response.text or ""
        names = _parse_names(text)
        logger.info("Discovered %d conferences via Gemini grounding", len(names))
        return names
    except Exception as exc:
        logger.error("Failed to discover conferences: %s", exc)
        return []


async def main() -> None:
    load_dotenv()
    logger.info("Starting conference discovery job")

    discovered = await discover_conferences()
    if not discovered:
        logger.warning("No conferences discovered. Exiting without updating KV.")
        return

    existing = await get_conferences()
    logger.info("Existing conferences in KV: %d", len(existing.conferences))

    updated = merge_conferences(existing, discovered)
    await write_conferences(updated)
    logger.info(
        "Conference list updated: %d total (%d new)",
        len(updated.conferences),
        len(updated.conferences) - len(existing.conferences),
    )


if __name__ == "__main__":
    asyncio.run(main())
