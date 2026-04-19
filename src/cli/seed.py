"""デフォルト設定を Cloudflare KV に seed するコマンド。

使い方: python -m src.seed

src/core/config.py のデフォルトソース・カテゴリを UserSettings v2 形式で
KV の default_settings キーに書き込む。dashboard の「ソースを初期化する」
ボタンがこのキーを参照する。
"""

import asyncio
import logging

from dotenv import load_dotenv

from src.core.runtime_config import build_default_user_settings
from src.services.storage.preferences import write_default_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    load_dotenv()
    defaults = build_default_user_settings()
    logger.info(
        "Seeding default_settings: %d sources, %d categories",
        len(defaults.sources or []),
        len(defaults.category_defs or []),
    )
    await write_default_settings(defaults)
    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
