"""src/core と dashboard/functions/api の契約整合性テスト。

型フィールドの整合性は scripts/gen_types.py の自動生成 + CI ドリフト検出で担保する。
ここでは KV キー名とデフォルト設定の整合性のみ検証する。
"""

import re
from pathlib import Path

from src.core import kv_keys
from src.core.runtime_config import build_default_user_settings

DASHBOARD_FUNCTIONS = Path(__file__).parent.parent / "dashboard" / "functions" / "api"


def _ts_const_string_values(ts_source: str) -> dict[str, str]:
    """export const FOO = "bar"; 形式の文字列定数を {FOO: "bar"} として返す。"""
    result: dict[str, str] = {}
    for m in re.finditer(r'export\s+const\s+(\w+)\s*=\s*"([^"]+)"', ts_source):
        result[m.group(1)] = m.group(2)
    return result


# ── KV キー名整合性 ─────────────────────────────────────────────────────────────

def test_kv_keys_match_ts() -> None:
    kv_keys_ts = (DASHBOARD_FUNCTIONS / "_kv_keys.ts").read_text()
    ts_consts = _ts_const_string_values(kv_keys_ts)

    py_key_map = {
        "KV_PREFERENCES": kv_keys.KV_PREFERENCES,
        "KV_LAST_ARTICLES": kv_keys.KV_LAST_ARTICLES,
        "KV_SETTINGS": kv_keys.KV_SETTINGS,
        "KV_DEFAULT_SETTINGS": kv_keys.KV_DEFAULT_SETTINGS,
        "KV_ARTICLE_INDEX": kv_keys.KV_ARTICLE_INDEX,
    }
    for py_name, py_val in py_key_map.items():
        assert py_name in ts_consts, f"{py_name} not found in _kv_keys.ts"
        assert ts_consts[py_name] == py_val, (
            f"KV key mismatch for {py_name}: py={py_val!r}, ts={ts_consts[py_name]!r}"
        )


# ── デフォルト設定の整合性 ──────────────────────────────────────────────────────

def test_build_default_user_settings_has_sources_and_categories() -> None:
    defaults = build_default_user_settings()
    assert defaults.sources is not None and len(defaults.sources) > 0
    assert defaults.category_defs is not None and len(defaults.category_defs) > 0


def test_build_default_user_settings_all_enabled() -> None:
    defaults = build_default_user_settings()
    assert all(s.enabled for s in (defaults.sources or []))
    assert all(c.enabled for c in (defaults.category_defs or []))
