"""src/core と dashboard/functions/api の契約整合性テスト。

Python 側 (Pydantic モデル / kv_keys.py) と TypeScript 側 (_types.ts / _kv_keys.ts) が
同期していることを検証する。TS ファイルを正規表現でパースして比較する。
"""

import re
from pathlib import Path

from src.core import kv_keys
from src.core.models import CategoryDef, SourceDef, UserSettings
from src.core.runtime_config import build_default_user_settings

DASHBOARD_FUNCTIONS = Path(__file__).parent.parent / "dashboard" / "functions" / "api"


# ── ユーティリティ ──────────────────────────────────────────────────────────────

def _ts_interface_fields(ts_source: str, interface_name: str) -> set[str]:
    """TypeScript interface の非オプショナル・オプショナル含むフィールド名を抽出する。"""
    pattern = rf"interface\s+{interface_name}\s*\{{([^}}]+)\}}"
    m = re.search(pattern, ts_source, re.DOTALL)
    assert m, f"interface {interface_name} not found"
    body = m.group(1)
    # "fieldName?:" or "fieldName:" から名前だけ取り出す
    return {
        field.strip().rstrip("?")
        for line in body.splitlines()
        if (field := line.strip().split(":")[0]) and not field.startswith("//")
    } - {""}


def _ts_const_string_values(ts_source: str) -> dict[str, str]:
    """export const FOO = "bar"; 形式の文字列定数を {FOO: "bar"} として返す。"""
    result: dict[str, str] = {}
    for m in re.finditer(r'export\s+const\s+(\w+)\s*=\s*"([^"]+)"', ts_source):
        result[m.group(1)] = m.group(2)
    return result


# ── 型フィールド整合性 ──────────────────────────────────────────────────────────

def test_source_def_fields_match() -> None:
    types_ts = (DASHBOARD_FUNCTIONS / "_types.ts").read_text()
    ts_fields = _ts_interface_fields(types_ts, "SourceDef")
    py_fields = set(SourceDef.model_fields.keys())
    assert py_fields == ts_fields, f"SourceDef mismatch: py={py_fields}, ts={ts_fields}"


def test_category_def_fields_match() -> None:
    types_ts = (DASHBOARD_FUNCTIONS / "_types.ts").read_text()
    ts_fields = _ts_interface_fields(types_ts, "CategoryDef")
    py_fields = set(CategoryDef.model_fields.keys())
    assert py_fields == ts_fields, f"CategoryDef mismatch: py={py_fields}, ts={ts_fields}"


def test_user_settings_fields_match() -> None:
    types_ts = (DASHBOARD_FUNCTIONS / "_types.ts").read_text()
    ts_fields = _ts_interface_fields(types_ts, "UserSettings")
    py_fields = set(UserSettings.model_fields.keys())
    assert py_fields == ts_fields, f"UserSettings mismatch: py={py_fields}, ts={ts_fields}"


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

def test_build_default_user_settings_is_v2() -> None:
    defaults = build_default_user_settings()
    assert defaults.schema_version == 2
    assert defaults.sources is not None and len(defaults.sources) > 0
    assert defaults.category_defs is not None and len(defaults.category_defs) > 0


def test_build_default_user_settings_all_enabled() -> None:
    defaults = build_default_user_settings()
    assert all(s.enabled for s in (defaults.sources or []))
    assert all(c.enabled for c in (defaults.category_defs or []))
