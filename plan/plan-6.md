# Gemini プロンプトのダッシュボード編集 素案 (plan-6)

> **素案**: plan-5-2 完了後に着手。設計はここで概要を示すが、詳細は実装前に再確認する。

前提: plan-5-2 完了済み。`UserSettings` v2 スキーマが存在し、fetcher が `RuntimeConfig` 経由で設定を読んでいる。

---

## Context

### 現状 (`gemini_selector.py:43-60`)
Gemini へのシステムプロンプトは関数内に f-string でハードコードされている。変えたい部分:

| 変更ニーズ | 現在の場所 | 変更頻度 |
|---|---|---|
| 選定基準の優先順位・文言 | L48-53 固定文字列 | たまに |
| 除外基準の文言 | L54-58 固定文字列 | たまに |
| 優先トピックの補足 (カテゴリ横断) | 注入点なし | 頻繁 |
| カテゴリごとの追加指示 | 注入点なし | ときどき |

### 設計の難しさ
- プロンプト本体をそのまま UI で編集可能にすると、不正な JSON 要求などで Gemini が壊れる。
- カテゴリ定義 (`category_defs[].keywords`) はすでに plan-5-1/5-2 で動的化済み — 「優先トピック」は実質的にここに集約されている。
- 最小リスクで最大効果を狙うなら「本体はハードコード維持、注入点だけ開ける」戦略が適切。

---

## 設計方針

プロンプト本体はハードコードを維持し、以下 2 つの**安全な注入点**を `UserSettings` に追加する:

### 注入点 1: `prompt_extra_criteria: list[str]`
カテゴリ横断で全プロンプトの末尾に追加されるカスタム指示（箇条書き形式）。

```
例: ["Rustに関する記事を優先", "アーキテクチャ設計の記事を重視"]
→ プロンプトに追加: 「追加指示:\n- Rustに関する記事を優先\n- アーキテクチャ設計の記事を重視」
```

### 注入点 2: `category_defs[].extra_prompt: str` (plan-5-2 の `CategoryDef` を拡張)
カテゴリごとの追加指示。そのカテゴリのプロンプトのみに付加する。

```
例: backend カテゴリに「特に Go / Rust / Java 系を優先」
→ backend のプロンプトのみに追記
```

---

## スキーマ拡張

`UserSettings` に追加:
```python
prompt_extra_criteria: list[str] = []  # 全カテゴリ横断の追加指示
```

`CategoryDef` に追加:
```python
extra_prompt: str = ""  # カテゴリ固有の追加指示
```

---

## 実装範囲

### Python 側 (`src/`)
- `src/models.py`: `UserSettings.prompt_extra_criteria` と `CategoryDef.extra_prompt` を追加。
- `src/selector/gemini_selector.py`: `_build_system_prompt` に `extra_criteria` と `extra_prompt` 引数を追加し、末尾に注入。
- `src/runtime_config.py`: `RuntimeConfig` に `prompt_extra_criteria` を追加。

### ダッシュボード側 (`dashboard/`)
- `dashboard/functions/api/_types.ts`: スキーマに同フィールドを追加。`UserSettings.prompt_extra_criteria` と `CategoryDef.extra_prompt`。
- `dashboard/app/settings/page.tsx` または `components/CategoryEditor.tsx`: 
  - 設定ページに「Gemini 追加指示」セクションを追加。
  - `prompt_extra_criteria`: Chip 入力（既存 `KeywordList` コンポーネントと同じ UI）。
  - カテゴリ編集モーダルに `extra_prompt` テキストエリア（1 行）を追加。

---

## 実装ステップ

### Step 1: スキーマ拡張 (Python + TS)
- [ ] `src/models.py` と `dashboard/functions/api/_types.ts` を同時に更新。

### Step 2: `gemini_selector.py` の注入点実装 (TDD)
- [ ] `tests/test_selector.py` に `extra_criteria` / `extra_prompt` が含まれるプロンプトのテストを追加。
- [ ] `_build_system_prompt` を修正して green に。

### Step 3: `RuntimeConfig` 更新
- [ ] `build_runtime_config` が `prompt_extra_criteria` を渡すように更新。
- [ ] `tests/test_runtime_config.py` に該当ケースを追加。

### Step 4: ダッシュボード UI 追加
- [ ] 設定ページに「Gemini 追加指示」セクション（Chip 入力）。
- [ ] カテゴリ編集に `extra_prompt` 入力欄（1 行テキストエリア）。

---

## 将来の拡張（このプランには含めない）

以下は意図的にスコープ外とする（プロンプト全体の編集は事故リスクが高いため）:
- 選定基準・除外基準の文言自体を UI で編集
- カテゴリごとにプロンプト全体を差し替える
- A/B テスト用の複数プロンプトバリアント管理

これらが必要になった時点で plan-7 として設計する。

---

## 検証

1. `pytest tests/ -v` グリーン。
2. `prompt_extra_criteria: ["Rustを優先"]` を設定して `python -m src.main` 実行 → Gemini に渡るプロンプトにその文字列が含まれること（デバッグログで確認）。
3. ダッシュボードで設定 → 保存 → リロードで保持。
