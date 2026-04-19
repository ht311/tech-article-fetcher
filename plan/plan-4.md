# Web ダッシュボード (Cloudflare Pages) 実装計画 (plan-4)

## Context

- **現状**: 配信された記事は LINE トーク履歴にしか残らず、数日前の記事を振り返るのが難しい。`preferences` / `last_articles` は KV に入っているが、ユーザーが直接閲覧する手段がない。設定（カテゴリON/OFF、ソース選択、件数）はコード側で固定され、変更には git push が必要。
- **問題**: (1) 過去記事に到達できない (2) どのソース・カテゴリが自分に刺さっているか数値で見えない (3) 設定変更のコストが高い
- **ゴール**: 自分だけがログインできる Web ダッシュボードを Cloudflare Pages に構築し、**過去記事の閲覧／統計の可視化／配信設定の編集** を実現する。設定は既存の配信バッチ（`src/main.py`）からも読み込まれ、配信挙動に反映する。

---

## 設計方針

### デプロイ構成: Pages プロジェクトを新設（既存 Worker は触らない）

| 案 | 長所 | 短所 |
|---|---|---|
| A) 既存 Worker に `/api/*`・`/dashboard` を足す | デプロイ対象 1 つ | Webhook とダッシュボードの責務が混在、静的アセット配信が弱い |
| **B) Pages プロジェクトを新設し、Pages Functions で API を実装（推奨）** | 静的配信＋API が同居、ルーティングが明快、Webhook Worker は無改修 | デプロイ対象が 2 つに増える |
| C) Pages に Webhook も移行 | 統一感 | 既存の安定稼働を壊すリスク |

→ **B 案** を採用。既存 Worker (`tech-article-fetcher-webhook`) は webhook 専用で据え置き、Pages (`tech-article-fetcher-dashboard`) を新規作成する。KV は同じ Namespace をバインド共有する。

### 認証: Cloudflare Access (Google OAuth, Email 許可リスト)

- 単一ユーザー想定なので、自前で OAuth を書くより **Cloudflare Access** に任せるのがコード量ゼロで安全。
- Pages プロジェクトに Zero Trust Application を紐付け、ポリシーで自分のメールだけを許可。
- Pages Functions 側では `Cf-Access-Jwt-Assertion` ヘッダー or `Cf-Access-Authenticated-User-Email` を信頼ベースで使う（Cloudflare 側で検証済）。
- 既存 LINE Webhook 側と認証スキームが異なるが、用途が違うので問題なし。

### フロントエンド: Next.js + Tailwind CSS + Recharts

- ユーザーが慣れている Next.js を採用（App Router）。
- Pages との統合: `output: 'export'` で静的書き出し → Cloudflare Pages にデプロイ。Pages Functions は `functions/` ディレクトリに置く（Next.js API Routes ではなく）。
- スタイルは Tailwind CSS。グラフは Recharts（React エコシステムと親和性が高い）。

---

## アーキテクチャ / データ構造

### KV キーの拡張

| キー | 形式 | 既存/新規 | 用途 |
|---|---|---|---|
| `preferences` | `{history: ArticleFeedback[]}` | 既存 | 評価履歴（最大100件） |
| `last_articles` | `{"1": {title, source, url}, ...}` | 既存 | 最新バッチ（Webhook 照合用） |
| `articles:YYYY-MM-DD` | `[{title, source, url, category_id, reason, thumbnail_url, published_at}, ...]` | **新規** | 日別の配信履歴 |
| `article_index` | `{dates: ["2026-04-19", "2026-04-18", ...]}` | **新規** | 配信日リスト（最大90日） |
| `settings` | `UserSettings` JSON | **新規** | 配信設定（カテゴリ・ソース・件数・除外キーワード） |

### UserSettings スキーマ（`src/models.py` に追加）

```python
class UserSettings(BaseModel):
    categories: dict[str, bool] = {
        "backend": True, "frontend": True, "aws": True,
        "management": True, "others": True,
    }
    sources_enabled: dict[str, bool] = {}  # 空 dict は「全部ON」扱い
    max_per_category: int = 5              # 1〜5
    exclude_keywords: list[str] = []       # タイトル/サマリに含まれたら除外
    include_keywords: list[str] = []       # 含まれていたら Gemini プロンプトに追加
```

---

## 実装ステップ

### Step 1: `src/models.py` — `UserSettings` モデル追加

`Article`/`SelectedArticle` と同じ位置に Pydantic モデルを定義。デフォルト値で KV 未設定時もそのまま動作。

### Step 2: `src/storage/preferences.py` — 設定と記事履歴の読み書き

追加する関数:

- `async def get_settings() -> UserSettings` — KV `settings` を読む。なければデフォルト。
- `async def write_article_history(date: str, selections: dict[str, list[SelectedArticle]]) -> None` — `articles:YYYY-MM-DD` と `article_index` を更新（90日を超える古い日付キーは index からドロップし対応 KV キーを削除）。

既存の `get_preferences` / `write_last_articles` は無改修。

### Step 3: `src/main.py` — 設定反映 & 履歴保存

- `get_settings()` を `get_preferences()` と並列で取得。
- `bucket_articles` の直後で:
  - `settings.categories` が False のカテゴリは空リスト化
  - `settings.sources_enabled` が False のソースを除外
  - `settings.exclude_keywords` にマッチする記事を除外
- `select_articles_by_category` に `max_per_category` と `include_keywords` を渡し、Gemini プロンプトに加える。
- 送信後に `write_article_history(today, selections)` を呼ぶ。

### Step 4: `src/selector/gemini_selector.py` — `max_per_category` と `include_keywords` の注入

既存の `SELECT_MAX_PER_CATEGORY` 定数を引数化。システムプロンプトに「ユーザーが関心あるキーワード: ...」を追記（空なら何もしない）。

### Step 5: `dashboard/` — Next.js プロジェクト作成

```
dashboard/
├── next.config.ts             # output: 'export'
├── package.json
├── tailwind.config.ts
├── tsconfig.json
├── src/
│   └── app/
│       ├── layout.tsx         # 共通レイアウト
│       ├── page.tsx           # / ダッシュボード（サマリー）
│       ├── articles/page.tsx  # 過去記事一覧（日付別）
│       ├── stats/page.tsx     # グラフ（Recharts）
│       └── settings/page.tsx  # 設定編集フォーム
└── functions/
    └── api/
        ├── articles.ts        # GET /api/articles?from=&to=
        ├── stats.ts           # GET /api/stats
        ├── preferences.ts     # GET /api/preferences
        └── settings.ts        # GET / PUT /api/settings
```

Next.js は静的書き出し（`output: 'export'`）で Pages に配信。Pages Functions（`functions/api/*.ts`）は KV バインディング (`env.KV`) で既存 Worker と同じデータを読み書き。

### Step 6: `terraform/main.tf` — Pages プロジェクト & Access 定義

```hcl
resource "cloudflare_pages_project" "dashboard" {
  account_id        = var.cloudflare_account_id
  name              = "tech-article-fetcher-dashboard"
  production_branch = "main"
  deployment_configs {
    production {
      kv_namespaces = {
        KV = cloudflare_workers_kv_namespace.preferences.id
      }
    }
  }
}

resource "cloudflare_access_application" "dashboard" {
  account_id       = var.cloudflare_account_id
  name             = "Tech Article Dashboard"
  domain           = "<pages-project>.pages.dev"
  type             = "self_hosted"
  session_duration = "24h"
}

resource "cloudflare_access_policy" "dashboard_owner" {
  application_id = cloudflare_access_application.dashboard.id
  account_id     = var.cloudflare_account_id
  name           = "Owner only"
  precedence     = 1
  decision       = "allow"
  include { email = [var.owner_email] }
}
```

`variables.tf` に `owner_email` を追加。

### Step 7: `.github/workflows/dashboard-deploy.yml` — Pages デプロイワークフロー

`dashboard/` 配下の変更時に Wrangler で Pages にデプロイ。daily-fetch.yml とは独立。

### Step 8: テスト

- `tests/test_settings.py` — `UserSettings` のデフォルト、フィルタロジックのユニットテスト。
- `tests/test_main_filter.py` — settings を使ったフィルタリングの結合テスト（Mock KV）。
- Pages Functions 側は最小限の unit test（Miniflare or vitest）。フロントエンドは手動確認で可。

---

## テスト方針

```bash
# Python 側
pytest tests/test_settings.py tests/test_main_filter.py -v
mypy src/
ruff check src/ tests/

# ダッシュボード側
cd dashboard
npm run build              # Next.js 静的書き出し成功（out/ 生成）
npx wrangler pages dev     # ローカル起動、/api/settings を curl

# 統合確認
# 1. ダッシュボードで categories.backend を false に
# 2. GitHub Actions を手動実行 → backend カテゴリがスキップされる
# 3. ダッシュボードの /articles に今日の配信が表示される
```

---

## 不明点・確認事項

[Q1] 認証は **Cloudflare Access + Google OAuth**（コード量ゼロ、メール許可リスト）で進めて良いか？ LINE Login OAuth が良ければ差し替える（実装コスト大）。
[A1] y

[Q2] フロントエンドは **Astro + Alpine.js + Chart.js** で良いか？ React/Next に慣れていてそちらが良ければ変更する。
[A2] React/Next 慣れているので

[Q3] 過去記事の保持期間は **90日** で十分か？ 長期保持したいなら `article_index` のローテート閾値を調整する。
[A3] y

[Q4] 設定編集のスコープはどこまで広げるか？（複数選択可）
  - (a) カテゴリ ON/OFF
  - (b) ソース ON/OFF（RSS 13 + Qiita + dev.to + HN + Reddit + SpeakerDeck）
  - (c) カテゴリあたりの最大件数
  - (d) 除外キーワード / 優先キーワード
  - (e) カテゴリ別選定観点（backend のプロンプト微調整など）
[A4] 全て

[Q5] ダッシュボードのドメインは `*.pages.dev` のままで良いか、独自ドメインを紐付けたいか？
[A5] `*.pages.dev` のままで良い

[Q6] Webhook Worker とダッシュボードで KV の書き込みキーが被らない認識（Webhook → `preferences`、ダッシュボード → `settings`）で良いか？
[A6] y
