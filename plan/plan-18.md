# 選定品質の改善 実装計画 (plan-18)

## Context

- **現状**:
  - `src/core/config.py:48-50` — `GEMINI_MODEL` と `GEMINI_FALLBACK_MODEL` が両方 `"gemini-2.5-flash"`。`gemini_selector.py:178` のフォールバックループは正しく動くが、切替先が同一モデルのため日次クォータ枯渇時に同じ枯渇モデルを再試行するだけの no-op。
  - `src/core/config.py:106` — `SEMANTIC_DEDUP_THRESHOLD = 0.88` がハードコード（コードベース唯一の「要調整」マーカー）。KV 設定で上書きできない。
  - `src/core/config.py:64-93` — カテゴリキーワードが浅い（aws は `aws`/`amazon web services` の2語のみ等）。多くの記事が `others` に落ちる。`categorizer.py:16` は単純部分文字列マッチのため、短い略語（ecs/eks/rds）を素朴に足すと "specs"/"geeks"/"words" に誤爆する。
- **問題**: クォータ枯渇時の劣化パスが機能しない・dedup 閾値の調整に コード変更とデプロイが必要・カテゴリ分類の取りこぼしが多い。
- **ゴール**: ①実効性のあるフォールバックモデル ②`semantic_dedup_threshold` の KV 設定化 + ダッシュボード UI ③単語境界マッチ導入とキーワード拡充による分類精度向上。

**ユーザー確認済みの方針**: aws カテゴリは「AWS 専用」のまま（クラウド全般には広げない）。ダッシュボード UI は**スコープに含める**。

---

## 設計方針

| 論点 | 選択 | 理由 |
|---|---|---|
| フォールバックモデル | `gemini-2.5-flash-lite` | 無料枠あり・RPD 上限は flash より大。切替ロジック（`_call_gemini` が 429+PerDay で即 raise → 次モデルへ）は既存のまま流用可 |
| JSON 逸脱対策 | `response_mime_type="application/json"` を GenerateContentConfig に追加 | 軽量モデルは JSON 逸脱頻度が上がる。両モデルに効き既存動作にも安全側 |
| 閾値の設定化 | `UserSettings.semantic_dedup_threshold: float \| None`（None → コードデフォルト 0.88） | `article_fetch_hours` / `gemini_max_input_per_category` と同一の既存パターン（`runtime_config.py:58-67`） |
| UI 実装 | `settings/page.tsx` に B·Press 調のセクションを直接追加 | `ParamsEditor.tsx` はオーファンかつ旧 Tailwind デザインで現行プレス調と不整合。復活させず、既存ページの意匠に合わせて実装 |
| classify | ASCII キーワードのみ `\b` 単語境界マッチ、日本語は従来の部分一致 | 日本語に `\b` は機能しない。正規表現は `lru_cache` でコンパイルキャッシュ |
| `_fallback_selection()` の品質ガード | **見送り** | `bucket_articles()`（categorizer.py:39-47）が嗜好スコア降順ソート済みのため `articles[0]` は既に最良候補。docstring 追記のみ |

---

## アーキテクチャ / データ構造

```python
# src/core/models.py — UserSettings に追加
semantic_dedup_threshold: float | None = Field(default=None, ge=0.5, le=1.0)

# src/core/runtime_config.py — RuntimeConfig に追加
semantic_dedup_threshold: float  # マージ後は必ず値を持つ
```

- 型再生成: `python scripts/gen_types.py` → `dashboard/functions/api/_types.generated.ts` に `semantic_dedup_threshold?: number | null` が追加される。**再生成コミット必須**（`type-drift.yml` CI が diff 検出で落ちる）。
- `dashboard/functions/api/settings.ts:13` `validateSettings()` に 0.5–1.0 のバリデーション追加。
- `tests/test_contract.py` は KV キー名検証のみのため変更不要。

---

## 実装ステップ

### Step 1: Gemini フォールバックモデルの実体化

[x] **Red** — `tests/test_selector.py` に追加:
  - `test_fallback_model_differs_from_primary` — `GEMINI_MODEL != GEMINI_FALLBACK_MODEL`（主バグの再発防止）
  - `test_daily_quota_switches_to_fallback_model` — 既存 `test_select_articles_by_category_empty_on_gemini_failure`（253行）のモックを踏襲。side_effect = [429 PerDay 例外, 正常 JSON]。2回目の `model` kwarg が fallback / 呼び出し計2回 / 結果非空を検証
  - `test_model_loop_skips_duplicate_model` — 両定数が同値でも同一モデルを2周しない
[x] **Green** — `src/core/config.py:50` を `"gemini-2.5-flash-lite"` に変更、49行目コメント修正
[x] `src/services/selector/gemini_selector.py:178` を `for model in dict.fromkeys((GEMINI_MODEL, GEMINI_FALLBACK_MODEL)):` に（設定退行時の防御）
[x] `gemini_selector.py:170` の `GenerateContentConfig` に `response_mime_type="application/json"` を追加（既存 success テストで回帰確認）
[x] `gemini_selector.py:147` docstring に「バケットは嗜好スコア/新しさ降順ソート済みのため先頭が最良候補」と追記

### Step 2: `semantic_dedup_threshold` の設定化（Python 側）

[x] **Red** — `tests/test_settings.py`: 0.5/1.0 受理、0.3/1.2 で ValidationError
[x] **Red** — `tests/test_runtime_config.py`: デフォルト時 0.88 / `UserSettings(semantic_dedup_threshold=0.75)` 時 0.75（既存 52-61 行と同型）
[x] **Green** — `src/core/models.py:60-69` にフィールド追加（`Field` import 追加）
[x] `src/core/runtime_config.py` — `RuntimeConfig` にフィールド追加、`build_runtime_config()` にマージ処理（`article_fetch_hours` パターン）
[x] `src/cli/main.py` — `SEMANTIC_DEDUP_THRESHOLD` import を削除し、`semantic_dedup(...)` 呼び出し（197-199行付近）を `rc.semantic_dedup_threshold` に置換
[x] `src/core/config.py:106` コメントを「KV の settings.semantic_dedup_threshold で上書き可」に更新
[x] `python scripts/gen_types.py` 実行 → `_types.generated.ts` の diff をコミットに含める

### Step 3: ダッシュボード UI + API バリデーション

[x] **Red** — `dashboard/functions/api/settings.test.ts`: `semantic_dedup_threshold` 0.5/1.0 受理・0.3/1.2/非数値で 400
[x] **Green** — `settings.ts` `validateSettings()` に範囲チェック追加
[x] `dashboard/app/settings/page.tsx` — カテゴリセクションの下に「選定チューニング」セクションを追加:
  - B·Press 調（既存の SectionLabel/インラインスタイル踏襲、`ParamsEditor.tsx` は使わない）
  - `type="range"`（0.5–1.0, step 0.01）+ 数値表示。説明文に「値が高いほど重複判定が厳しくなる（1.0 で実質無効）」を明記
  - 保存は既存 `toggleCategory` と同じ PUT パターン（サーバー側マージなので threshold のみ送信でも可）
[x] dashboard の lint/型/テスト（biome + tsc + vitest）通過確認

### Step 4: classify の単語境界マッチ + カテゴリキーワード拡充

[x] **Red** — `tests/test_selector.py` classify テスト群（70-117行）に追加:
  - 誤爆防止: "Writing better specs" → others（ecs）、"5000 words essay" → others（rds）、"Zero Trust Architecture" → others（rust）
  - 新キーワード: "DynamoDB のインデックス設計" → aws、"Lambda コールドスタート対策" → aws、"Vue 3 の Composition API" → frontend、"スクラムイベントの改善" → management
  - 日本語は従来通り部分一致: "組織づくりの話" → management
[x] **Green** — `src/services/selector/categorizer.py` に `_kw_match(kw, text)` を追加:
  - ASCII のみのキーワード → `re.search(rf"\b{re.escape(kw)}\b", text)`（`lru_cache` でコンパイルキャッシュ）
  - 非 ASCII を含む → 従来の `kw in text`
[x] `src/core/config.py:64-93` キーワード拡充:
  - **backend** 追加: jvm, graalvm, kotlin, quarkus, hibernate, jpa, jakarta, maven, gradle, mysql, sql, grpc, kafka, redis, golang, rust, マイクロサービス, バックエンド（`go` 単体は境界マッチでも誤爆過多のため不可）
  - **frontend** 追加: javascript, vue, nuxt, svelte, angular, css, tailwind, vite, フロントエンド
  - **aws** 追加（AWS 専用）: ec2, s3, ecs, eks, fargate, lambda, dynamodb, rds, aurora, cloudfront, cloudformation, cloudwatch, sqs, kinesis, bedrock, sagemaker, step functions, eventbridge, cdk（iam は Azure/GCP 記事にも頻出、sns は日本語でソーシャルメディアの意味が支配的なため除外）
  - **management** 追加: scrum, スクラム, agile, アジャイル, テックリード, tech lead, okr, 心理的安全性, psychological safety, ふりかえり, レトロスペクティブ, retrospective, オンボーディング, 人事評価（「採用」「評価」単体は技術文脈での誤爆多発のため除外）

### Step 5: 仕上げ

[x] `pytest tests/ -v` / `ruff check src/ tests/` / `mypy src/` 全通過
[x] dashboard: biome + tsc + vitest 通過
[x] doc-sync で README 更新（フォールバックモデル・設定項目追加・キーワード方針）→ コミット → push → PR 起票

---

## テスト方針

- `tests/test_selector.py` — フォールバック切替（モック side_effect 2段）、classify 境界マッチ/新キーワード/誤爆防止
- `tests/test_settings.py` / `tests/test_runtime_config.py` — 新フィールドのバリデーション境界とマージ
- `dashboard/functions/api/settings.test.ts` — API バリデーション境界
- 既存 112 テストの回帰確認（特に `response_mime_type` 追加後の selector success 系）

---

## 不明点・確認事項

[Q1] KV の `settings` キーに `category_defs` が既に保存されている場合、`runtime_config.py:47-50` はそれを優先するため Step 4 の新キーワードは反映されません。デプロイ後に KV の `settings.category_defs` を一度リセット（削除 or ダッシュボードから再保存）する運用で良いですか？
[A1] はい（ユーザー一任）。デプロイ後に KV の `settings.category_defs` をリセット（ダッシュボードから再保存 or キー内の category_defs を削除）する。手順を PR 説明に記載する。

[Q2] classify の単語境界マッチ導入でマッチ挙動が厳格化されます（例: 現在 "awsome" が aws にマッチするケースは外れる）。短い略語を安全に追加する前提条件のため導入推奨ですが、問題ないですか？
[A2] 導入する（ユーザー一任）。ただし実装は `\b` ではなく ASCII 英数字ルックアラウンド `(?<![a-z0-9])kw(?![a-z0-9])` を使う。`\b` は日本語文字も \w 扱いのため「lambdaで作る」「reactの新機能」のような日本語直結タイトルにマッチしなくなる退行があるため。

[Q3] `gemini-2.5-flash-lite` の無料枠・RPD 上限は実装時に最新のレート表で確認します。もし flash-lite が不適だった場合の代替（例: flash-lite-preview 系を避けて安定版のみ使う）はこちらの判断で進めて良いですか？
[A3] 任せてもらう（ユーザー一任）。安定版 `gemini-2.5-flash-lite`（無料枠あり・flash より高 RPD）を採用。
