# 記事参照定義の一元管理 実装計画 (plan-7 改訂版)

## Context

- **現状**: 「どの記事/ソースを参照するか」の定義が 3 モジュール (`src/` / `dashboard/` / `infrastructure/`) に散在し、互いに重複したハードコードを抱える。
- **ユーザーの要求 (A1)**: 言語非依存 JSON 等の外部 SSoT ではなく、**既存モジュールのうちいずれか 1 つに責務を寄せる**。
- **採用する所有者**: **`src/` (Python)** を唯一の責務モジュールとする。理由:
  - 記事のフェッチ・分類・選定・KV への書き込みを行っており、実データの生産者である
  - 既に `src/core/config.py` にデフォルト定義・Pydantic モデル・マージロジックが揃っている
  - dashboard/Worker は KV 消費者であり、データ発行者ではない
- **ゴール**: `dashboard/` と `infrastructure/` からは「どの記事ソース/カテゴリ/KV キー/定数を扱うか」に関するハードコードを全て除去し、**すべて src/ が KV と Worker env 経由で配布する**構造にする。

---

## 責務分担の原則

| データ種 | 所有モジュール | 配布経路 | 消費側 |
|---|---|---|---|
| ソース一覧 (RSS/Qiita/SpeakerDeck) | `src/core/config.py` | KV `default_settings` | dashboard (API), Worker (該当なし) |
| カテゴリ定義 (id / name / keywords / order) | `src/core/config.py` | KV `default_settings` & `settings` | dashboard (API) |
| カテゴリ日本語ラベル | `CategoryDef.name` (src/) | `/api/settings` の `category_defs[].name` | dashboard |
| デフォルト UserSettings snapshot | `src/core/runtime_config.py::build_default_user_settings` | KV `default_settings` | dashboard 初期化ボタン |
| KV キー名 | `src/core/kv_keys.py` (新設) | Worker env binding (Terraform で注入) | dashboard (Worker env 経由)、Worker (env 経由) |
| 共通定数 (`MAX_HISTORY` 等) | `src/core/constants.py` (新設) | Worker env binding | Worker |
| TS 型 (`SourceDef`/`CategoryDef`/`UserSettings`) | `src/core/models.py` (Pydantic が権威) | `dashboard/functions/api/_types.ts` を手書きミラーとし、**contract テストで drift 検出** | dashboard 全ファイル |
| Cloudflare リソース構成 | `infrastructure/terraform` | - | - |

**原則の帰結**:
- dashboard にカテゴリ ID (`"backend"` 等) やソース名 (`"Zenn"` 等) のリテラルが出現してはならない (色マップ等の純 UI 関心は除く)。
- infrastructure/cloudflare/index.js に KV キー文字列や `MAX_HISTORY` 数値リテラルが出現してはならない。

---

## 受け入れ基準 (検証可能なゴール状態)

1. `grep -rE '"(backend|frontend|aws|management|others)"' dashboard/app dashboard/functions` の結果がゼロ (ただし `CATEGORY_COLORS` 等の色マップキーは例外として許容)。
2. `grep -rE '"(Zenn|Qiita|SpeakerDeck)"' dashboard/` の結果がゼロ。
3. `pytest tests/test_contract.py` が green で、Python `models.py` と TS `_types.ts` のフィールド整合性を保証する。
4. `src/core/config.py` の `RSS_SOURCES` に 1 件追加 → `python -m src.seed` 実行 → dashboard の「ソース設定」画面に即座に反映される (リビルド不要)。
5. `pytest tests/ -v`、`ruff check src/ tests/`、`mypy src/`、dashboard の `npm test` が全て green。

※ `infrastructure/cloudflare/index.js` は今回スコープ外 (A1=c)。KV キー名・MAX_HISTORY のリテラルはコメントで `src/core/kv_keys.py` を参照元として明記する程度にとどめる。

---

## 実装ステップ

### Step 1: src/ 配下を責務モジュールとして整備

**1-a. `src/core/kv_keys.py` 新設** (KV キー名の唯一の定義場所):

```python
KV_PREFERENCES = "preferences"
KV_LAST_ARTICLES = "last_articles"
KV_SETTINGS = "settings"
KV_DEFAULT_SETTINGS = "default_settings"
KV_ARTICLE_INDEX = "article_index"
KV_ARTICLE_HISTORY_PREFIX = "articles:"
```

**1-b. `src/core/constants.py` 新設** (言語横断で共有が必要な定数):

```python
MAX_HISTORY = 100
ARTICLE_RETENTION_DAYS = 90
```

**1-c. 既存 `src/services/storage/preferences.py:22-27` から定数を kv_keys.py / constants.py に移動**。`preferences.py:81-92, 148, 157` の `from src.core.config import CATEGORIES` 直接 import を撤去し、`category_defs` を引数で受け取る形に変更 (動的カテゴリ対応)。

### Step 2: Python が KV に全カタログを seed するコマンドを提供

**2-a. `src/core/runtime_config.py` に `build_default_user_settings() -> UserSettings` 追加**。`default_sources()` + `default_category_defs()` を結合し v2 形式で返す。

**2-b. `src/services/storage/preferences.py` に `write_default_settings()` 追加**。既存 `write_user_settings` と同パターン。

**2-c. seed コマンド `src/cli/seed.py` 新設**:
```python
# python -m src.seed
async def main() -> None:
    defaults = build_default_user_settings()
    await write_default_settings(defaults)
```
`pyproject.toml` の `[project.scripts]` にも追加 (既存 main コマンドと同様)。

**2-d. 既存の定期ジョブ (`src/cli/main.py`) の先頭でも同 seed を呼ぶ**。→ `config.py` 変更が次回ジョブ起動で自動反映される。

### Step 3: dashboard/ から全ハードコード除去

**3-a. `dashboard/functions/api/defaults.ts` 新設** — KV `default_settings` を返すだけの GET エンドポイント。

**3-b. `dashboard/functions/api/_kv_keys.ts` 新設** — KV キー名の TS 側唯一定義。ファイル先頭コメントで `src/core/kv_keys.py` を参照元として明示。`articles.ts` / `settings.ts` / `stats.ts` / `preferences.ts` の文字列リテラルを全て import に置換。

**3-c. `dashboard/functions/api/_types.ts:46-58` の `DEFAULT_SETTINGS` を削除**。`settings.ts` で 404 時のフォールバックが必要なら内部で KV `default_settings` を読む実装に変更。

**3-d. `dashboard/app/settings/page.tsx:178-193`** の「ソースを初期化する」ボタン内ハードコード配列を削除し `fetch("/api/defaults")` に置換。

**3-e. `dashboard/app/page.tsx:20-26` / `articles/page.tsx:20-34` / `stats/page.tsx:26-32` の `CATEGORY_LABELS` 削除**。`/api/settings` の `category_defs[].name` から lookup する共通フック `dashboard/app/lib/useCategories.ts` を新設。`CATEGORY_COLORS` は UI 関心なので残す。

**3-f. `dashboard/app/components/SourceEditor.tsx:5-11` / `CategoryEditor.tsx:5-11` の型/ラベル再定義を削除** し、`_types.ts` から import。`TYPE_LABELS` は `_types.ts` に移動。

### Step 4: infrastructure/cloudflare/index.js — コメントで参照元を明示 (A1=c)

`index.js` は現状の単一ファイル運用を維持する。コードの変更はしないが、KV キー名リテラルおよび `MAX_HISTORY = 100` の直前に以下のコメントを追記する:

```js
// KV key names must match src/core/kv_keys.py
// MAX_HISTORY must match src/core/constants.py
```

→ contract テストは Py ⇔ TS のみ。JS の drift は手動確認 + コメントで抑制。

### Step 5: Contract テストで Python ⇔ TypeScript 整合性を保証

**5-a. `tests/test_contract.py` 新設**:
- `src/core/models.py` の Pydantic モデル (`SourceDef` / `CategoryDef` / `UserSettings`) の `model_json_schema()` を取得
- `dashboard/functions/api/_types.ts` を正規表現パースしてフィールド名を抽出
- フィールド名・オプショナリティが一致しないと fail

**5-b. `tests/test_contract.py` で KV キー名の整合性も検証**:
- `src/core/kv_keys.py` の定数と `dashboard/functions/api/_kv_keys.ts` / `infrastructure/terraform/main.tf` の plain_text_binding 値が一致することを検証

これにより TS/TF 側を手書きミラーで運用しても、drift は CI で即検出される。

---

## テスト方針

| 層 | 検証項目 |
|---|---|
| `src/core/runtime_config.py` | `build_default_user_settings()` が `default_sources()` / `default_category_defs()` と整合 |
| `src/services/storage/preferences.py` | `write_default_settings` が正しい JSON を PUT、`write_last_articles` が `category_defs` 引数を尊重 |
| `tests/test_contract.py` (新規) | Python モデル ⇔ TS `_types.ts` / TF `main.tf` のフィールド名・キー名整合性 |
| `dashboard/functions/api/defaults.test.ts` (新規) | `/api/defaults` が KV を返す / 未 seed で 404 |
| `dashboard/functions/api/settings.test.ts` | `DEFAULT_SETTINGS` 依存を撤去、`/api/defaults` スタブ化 |
| E2E 手動 | Python `python -m src.seed` → dashboard 再読込 → 初期化ボタンで最新ソース一覧取得 |

---

## 影響範囲サマリ

**新規**:
- `src/core/kv_keys.py`, `src/core/constants.py`
- `src/cli/seed.py`
- `dashboard/functions/api/defaults.ts`, `dashboard/functions/api/_kv_keys.ts`
- `dashboard/app/lib/useCategories.ts`
- `tests/test_contract.py`

**変更**:
- `src/core/runtime_config.py` (`build_default_user_settings` 追加)
- `src/services/storage/preferences.py` (定数移動、`write_default_settings` 追加、`category_defs` 引数化)
- `src/cli/main.py` (起動時 seed、`category_defs` 引き回し)
- `pyproject.toml` (scripts 追加)
- `dashboard/functions/api/_types.ts` (`DEFAULT_SETTINGS` 削除、`TYPE_LABELS` 追加)
- `dashboard/functions/api/settings.ts` / `articles.ts` / `stats.ts` / `preferences.ts` (KV キー import 化)
- `dashboard/app/settings/page.tsx` (初期化ボタンを /api/defaults 経由化)
- `dashboard/app/page.tsx` / `articles/page.tsx` / `stats/page.tsx` (`CATEGORY_LABELS` 削除、`useCategories` 利用)
- `dashboard/app/components/SourceEditor.tsx` / `CategoryEditor.tsx` (型/ラベル import 化)
- `infrastructure/cloudflare/index.js` (KV キー/定数を env 経由)
- `infrastructure/terraform/main.tf` (`plain_text_binding` 追加)
- `README.md` (責務分担を明記)

**コメント追記のみ**: `infrastructure/cloudflare/index.js` (A1=c)

**変更不要**: `src/core/config.py` (ここが SSoT)、`src/services/fetchers/*`、`src/services/selector/*`、`infrastructure/terraform/*.tf`

**新規 (実装外)**: `TODO.md` — 「TS 型定義の自動生成 (pydantic → TS) の導入 (A2=b)」を今後のタスクとして記録

---

## 不明点・確認事項

[Q1] Worker 側の KV キー名/`MAX_HISTORY` の扱いをどこまで厳格にしますか?
  - (a) **[推奨]** Terraform `plain_text_binding` で Worker env に注入、`index.js` はリテラルゼロ。contract テストで TF ⇔ Py を検証。
  - (b) `infrastructure/cloudflare/index.js` 先頭に `const KV_KEYS = {...}` ブロックを残し、コメントで `src/core/kv_keys.py` 参照。contract テストで JS ⇔ Py を検証。
  - (c) Worker は単一ファイル運用のまま、現状のリテラルを許容。リンターでの警告のみ。

[A1] c

[Q2] TS 型定義 (`_types.ts`) の同期方式は?
  - (a) **[推奨]** 手書きミラー + `tests/test_contract.py` で drift 検出 (本計画の前提)
  - (b) Pydantic → TS 自動生成ツール (例: `datamodel-code-generator` or `pydantic2ts`) を導入
  - (c) TS 側が唯一の型定義になるよう Python を刷新 (却下想定、責務寄せの方向に反する)

[A2] a,ただしtodo.mdを作成して、bをすることを記録

[Q3] Python seed の実行タイミング?
  - (a) 既存ジョブ (`python -m src.main`) の先頭で毎回実行
  - (b) 独立コマンド `python -m src.seed` のみ用意し、CI/CD の deploy step で明示的に実行
  - (c) **[推奨]** 両方。ジョブでも念のため実行しつつ、独立コマンドでデプロイ時に即時反映可能にする。

[A3] c

[Q4] `/api/defaults` が未 seed (404) のときの dashboard 挙動は?
  - (a) **[推奨]** 初期化ボタンを無効化し、「デフォルトが未 seed です。`python -m src.seed` を実行してください」と表示
  - (b) TS 側でエラーをユーザー表示せずサイレントに握りつぶす (現行挙動維持)

[A4] a

[Q5] `useCategories` フックは SWR や React Query 等のライブラリを導入しますか?
  - (a) **[推奨]** 依存追加なし。素の `useEffect` + `useState` で `/api/settings` を fetch してキャッシュ。
  - (b) SWR を導入してリバリデーションや共有キャッシュを得る。

[A5] a

---

## 完了条件

上記「受け入れ基準」の 7 項目がすべて満たされていること。
