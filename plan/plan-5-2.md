# dashboard / fetcher 設定ベース化 フェーズ2 — fetcher を設定ベースで動かす (plan-5-2)

前提: plan-5-1 完了済み（`UserSettings` v2 スキーマ拡張、ダッシュボード UI 拡張、KV への v2 保存が完了している状態）。

## Context

### 現状 (plan-5-1 完了後)
- `UserSettings` に v2 フィールド (`sources`, `category_defs`, `article_fetch_hours`, `gemini_max_input_per_category`) が追加済みだが、fetcher 側はこれらをまだ読んでいない。
- fetcher は引き続き `src/config.py` のモジュール定数を直接 import して動いている。
- `src/main.py` → `from config import RSS_SOURCES, CATEGORIES, QIITA_TAGS, ...` などが散在。
- 実装済み・未配線の fetcher: `hacker_news_fetcher`, `reddit_fetcher`, `devto_fetcher`。

### ゴール (このフェーズ)
- 起動時に KV の `settings` を読み、v2 フィールドがあればそれをベースに動作する。
- v2 フィールドが空なら `src/config.py` のデフォルトにフォールバックする。
- `config.py` への直接 import を fetcher/selector/notifier から除去し、`RuntimeConfig` 引数渡しに統一。
- 未配線の fetcher を `sources[].type` ディスパッチで有効化。

---

## 設計方針

- 「settings から読む → なければ config.py のデフォルトを使う」フォールバック戦略。
- `src/config.py` は**廃止せず、defaults 置き場として残す**（テスト・ローカル実行に必要）。
- `src/runtime_config.py` を新設: `RuntimeConfig` と `build_runtime_config()` を定義。
- `src/main.py` 冒頭で `settings → RuntimeConfig` を合成し、以降の全関数に引数で渡す。

---

## アーキテクチャ変更

```
旧: main.py → from config import RSS_SOURCES, CATEGORIES, ...（直接定数参照）
       ↓
新: main.py → get_settings() → build_runtime_config(settings) → RuntimeConfig
                                                                       ↓
                                                 fetchers / selector / notifier に引数渡し
```

---

## 新設ファイル: `src/runtime_config.py`

```python
class RuntimeConfig(BaseModel):
    sources: list[SourceDef]           # 有効なソース（enabled=True のみ）
    category_defs: list[CategoryDef]   # 有効なカテゴリ（enabled=True のみ、order 順）
    max_per_category: int
    article_fetch_hours: int
    gemini_max_input_per_category: int
    exclude_keywords: list[str]
    include_keywords: list[str]

def build_runtime_config(settings: UserSettings) -> RuntimeConfig:
    """
    v2 フィールドがあればそれを優先。なければ config.default_* を使う。
    v1 の categories / sources_enabled を重ね合わせて enabled フラグに反映する。
    """
    ...
```

`build_runtime_config` のマージロジック:
1. `sources` が設定済み → そのまま使用。v1 の `sources_enabled` を重ね合わせて enabled を上書き。
2. `sources` が未設定 → `config.default_sources()` で生成。v1 の `sources_enabled` を反映。
3. `category_defs` が設定済み → そのまま使用。v1 の `categories` ON/OFF を重ね合わせ。
4. `category_defs` が未設定 → `config.default_category_defs()` から生成。v1 `categories` を反映。
5. `article_fetch_hours` / `gemini_max_input_per_category` は設定値 or config デフォルト。

---

## 主要ファイル変更

| ファイル | 変更内容 |
|---|---|
| `src/runtime_config.py` | 新規。`RuntimeConfig` と `build_runtime_config()` |
| `src/main.py` | config 定数の直接参照を廃止。`RuntimeConfig` を作成して各関数に渡す |
| `src/fetchers/rss_fetcher.py` | `fetch_all_rss(sources: list[SourceDef], hours: int)` に変更 |
| `src/fetchers/qiita_fetcher.py` | `fetch_qiita(sources: list[SourceDef], hours: int)` — params から tags 等を取得 |
| `src/fetchers/speakerdeck_fetcher.py` | `fetch_speakerdeck(sources: list[SourceDef], hours: int)` — params からカテゴリ取得 |
| `src/fetchers/hacker_news_fetcher.py` | main から呼ぶ。`type == "hackernews"` のソースがあれば実行 |
| `src/fetchers/reddit_fetcher.py` | 同上。`params.subreddit` から subreddit 一覧を構築 |
| `src/fetchers/devto_fetcher.py` | 同上 |
| `src/selector/categorizer.py` | `classify(article, category_defs: list[CategoryDef])` に変更 |
| `src/selector/gemini_selector.py` | `category_defs` を受け取ってプロンプト構築。template はハードコード維持 |
| `src/notifier/line_notifier.py` | `_MAX_ARTICLES_PER_CATEGORY` 定数を廃止し `max_per_category` を引数で受ける。カテゴリ順を `category_defs[].order` で決定 |
| `src/config.py` | `default_sources()` / `default_category_defs()` を残し、各定数を内部化 |

---

## 実装ステップ

### Step 1: `RuntimeConfig` と `build_runtime_config()` — TDD (Red → Green)
- [ ] `tests/test_runtime_config.py` を先に書く:
  - (a) v2 `sources` + `category_defs` のみ → そのまま反映
  - (b) v1 `sources_enabled`/`categories` のみ → defaults に ON/OFF を重ね合わせ
  - (c) 空 `UserSettings` → 全 config デフォルト
  - (d) v2 フィールド + v1 ON/OFF の混在 → v2 ベースで v1 が上書き
- [ ] `src/runtime_config.py` を実装して全ケースをグリーンにする。

### Step 2: fetchers を引数駆動に変更
- [ ] `rss_fetcher`, `qiita_fetcher`, `speakerdeck_fetcher` から `from ..config import X` を除去し引数渡しに変更。
- [ ] `hacker_news_fetcher` / `reddit_fetcher` / `devto_fetcher` を削除（dead code）。
- [ ] `tests/test_fetchers.py` を更新。

### Step 3: categorizer / gemini_selector / line_notifier を引数駆動に
- [ ] `classify(article, category_defs)` に変更。
- [ ] `select_articles_by_category(buckets, category_defs, max_per_category, ...)` に変更。
- [ ] `send_articles(articles, category_defs, max_per_category)` に変更（`_MAX_ARTICLES_PER_CATEGORY` 廃止）。
- [ ] `tests/test_selector.py` / `tests/test_notifier.py` を更新。

### Step 4: `src/main.py` 再配線
- [ ] `load_dotenv` → `get_settings()` → `build_runtime_config(settings)` → fetchers → selector → notifier の流れに整理。
- [ ] `tests/test_settings.py` のフィルタ再現テスト（main.py ロジックの重複部分）を削除し、`build_runtime_config` テストに統合。

### Step 5: e2e スモーク確認
- [ ] `python -m src.main` でローカル 1 回実行、LINE に配信成功。
- [ ] ダッシュボードで Zenn を OFF → 翌バッチで Zenn 記事が来ないこと。
- [ ] ダッシュボードで新規 RSS ソースを追加 → 翌バッチでその記事が来ること。

---

## テスト方針

- TDD 原則: Step 1 は必ず Red → Green の順で。
- 既存テスト (`test_fetchers`, `test_selector`, `test_notifier`) は修正後も全グリーンを維持。
- `ruff check src/ tests/` と `mypy src/` を全ステップで通し確認。

---

## 検証

1. `pytest tests/ -v` 全グリーン
2. `ruff check src/ tests/` / `mypy src/` 全グリーン
3. `python -m src.main` が LINE に配信成功（ローカル `.env` 使用）
4. KV に v2 設定を入れた状態で実行 → カスタム設定が反映されること
5. KV に v1 設定のみの状態で実行 → デフォルト動作が変わらないこと（後方互換）

---

## 不明点・確認事項

[Q5] **スコープ**: Gemini モデル名 (`GEMINI_MODEL`) を `UserSettings` に入れて動的化するか？ 推奨は「今回は外す」（モデル変更時はデプロイで十分・事故リスクあり）。
[A5] 今回は外す

[Q6] **プロンプトテンプレート**: `gemini_selector.py:43-60` のプロンプト本体はハードコード維持でよいか？ 必要なら `settings.preferred_topics: list[str]` のような安全な注入点だけ開ける。
[A6] plan6.mdにダッシュボードで変更できるようにする素案を書いておいて

[Q7] **未配線 fetcher (HN / Reddit / dev.to)**: このフェーズで配線して有効化するか？ しない場合は dead code として削除するか継続保留か？
[A7] 削除

[Q8] **`line_notifier._MAX_ARTICLES_PER_CATEGORY`(L26) の廃止**: `max_per_category` 一本化に合意か？ Gemini 選定段階で件数は絞れるので notifier は受け取った分を送るだけにしたい。
[A8] ok

[Q9] **マルチユーザー対応**: `LINE_USER_ID` 単数のままで今回はスコープ外としてよいか？
[A9] ok
