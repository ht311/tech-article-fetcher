# tech-article-fetcher

Webエンジニア向けの技術記事を毎日自動収集し、LINEにカテゴリ別で配信するボット。  
GitHub Actions をスケジューラーとして使うことで **サーバーレス・ゼロインフラコスト** を実現。  
👍/👎 のフィードバックを学習し、日々の選定精度を向上させます。

## アーキテクチャ

```
GitHub Actions (cron: 毎日 JST 8:00)
  ↓
Python スクリプト (src/cli/main.py)
  ├── 記事収集（並列）
  │   ├── RSS: 13 フィード（日本語・企業・海外公式ブログ）
  │   ├── Qiita API（タグ別 8 並列 + 人気記事 1 件）
  │   ├── dev.to API（週間トップ）
  │   ├── Hacker News Firebase API（スコア ≥ 100）
  │   ├── Reddit JSON API（7 サブレディット、スコア ≥ 500）
  │   └── SpeakerDeck Atom（5 カテゴリ、日本語スライドのみ）
  ├── 重複排除（URL ベース）
  ├── Cloudflare KV からユーザー嗜好・配信設定を並列読み込み
  ├── キーワードマッチングで 5 カテゴリに分類
  │   （backend / frontend / aws / management / others）
  ├── 配信設定（UserSettings）に基づきフィルタ
  │   （カテゴリ ON/OFF・ソース ON/OFF・除外キーワード）
  ├── Gemini API (gemini-2.5-flash) でカテゴリ別に並列選定（件数・優先キーワード反映）
  ├── LINE Messaging API（Flex Message）でカテゴリ別に送信（最大 5 メッセージ）
  └── 送信記事リストを Cloudflare KV に書き込み（last_articles + 日別履歴）

Cloudflare Worker（常時稼働・無料）
  ├── LINE Webhook を受信・HMAC-SHA256 署名検証
  ├── "👍N" / "👎N" テキストをパース
  ├── KV の last_articles から記事情報を照合
  ├── KV の preferences に評価履歴を追記（最大 100 件でローテート）
  └── エラー時のみ返信（正常時は返信しない・メッセージ数節約）

Cloudflare Pages（ダッシュボード・常時稼働・無料）
  ├── Next.js 静的サイト（過去記事・統計・設定を閲覧／編集）
  ├── Pages Functions で API を提供（同一 KV Namespace を共有）
  │   ├── GET /api/articles   — 日別記事履歴
  │   ├── GET /api/stats      — フィードバック統計・週次トレンド
  │   ├── GET /api/preferences — 評価履歴
  │   └── GET/PUT /api/settings — 配信設定の取得・更新
  └── HTTP Basic Auth（DASHBOARD_SECRET 環境変数でパスワード保護）
```

## ディレクトリ構成

```
tech-article-fetcher/
├── .devcontainer/       # 開発コンテナ設定
├── .github/             # GitHub Actions ワークフロー
├── infrastructure/               # インフラストラクチャコード
│   ├── cloudflare/      # Cloudflare コンフィグ（Worker・KV）
│   └── terraform/       # Terraform でインフラ定義
├── src/                 # Python バックエンド
│   ├── cli/             # CLIエントリポイント
│   │   └── main.py      # メインスクリプト
│   ├── core/            # コアロジック・共有モデル
│   │   ├── config.py    # 設定（RSS・カテゴリ定義）
│   │   ├── models.py    # Pydantic データモデル
│   │   └── runtime_config.py  # ランタイム設定
│   └── services/        # ビジネスロジック・外部連携
│       ├── fetchers/    # 記事取得（RSS, Qiita, SpeakerDeck）
│       ├── selector/    # カテゴリ分類・記事選定（Gemini）
│       ├── notifier/    # LINE 通知
│       └── storage/     # Cloudflare KV 連携
├── dashboard/           # Web ダッシュボード（Next.js）
├── tests/               # ユニット・統合テスト
└── docs/                # ドキュメント
```

## セットアップ

### 1. 必要なもの

| 変数名 | 取得元 | 用途 |
|--------|--------|------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) | 記事選定 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers > Messaging API | LINE Push 送信 |
| `LINE_USER_ID` | ボットを友だち追加後に取得（`U` で始まる文字列） | 送信先 |
| `LINE_CHANNEL_SECRET` | LINE Developers > チャンネル基本設定 | Webhook 署名検証 |
| `CLOUDFLARE_API_TOKEN` | Cloudflare Dashboard | KV REST API 認証 |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Dashboard の URL | KV REST API |
| `CLOUDFLARE_KV_NAMESPACE_ID` | `terraform output kv_namespace_id` | KV 操作対象 |

Cloudflare API トークンに必要な権限: **Workers KV Storage: Edit**, **Workers Scripts: Edit**, **Cloudflare Pages: Edit**

### 2. Cloudflare リソースを作成（Terraform）

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars を編集して各値を設定

terraform init
terraform apply -auto-approve

# KV Namespace ID を控える（GitHub Secrets に登録する）
terraform output kv_namespace_id

# ダッシュボード URL を確認
terraform output dashboard_url
```

### 3. LINE Webhook URL を設定

Terraform apply 後、Cloudflare Dashboard > Workers & Pages で Worker の URL を確認し、  
LINE Developers コンソール > Messaging API > Webhook URL に設定してください。

### 4. GitHub Secrets を登録

リポジトリの **Settings > Secrets and variables > Actions** に以下の 7 変数を登録：

- `GEMINI_API_KEY`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_USER_ID`
- `LINE_CHANNEL_SECRET`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_KV_NAMESPACE_ID`

### 5. ダッシュボードをデプロイ

```bash
# dashboard/ を push すると GitHub Actions が自動デプロイ
# 手動デプロイの場合:
cd dashboard
npm ci && npm run build
npx wrangler pages deploy out --project-name=tech-article-fetcher-dashboard
```

ダッシュボードにパスワードを設定する（任意・推奨）:

1. Cloudflare Dashboard > Pages > `tech-article-fetcher-dashboard` > **Settings** > **Environment variables**
2. **Add variable** → Name: `DASHBOARD_SECRET` / Value: 任意のパスワード → **Encrypt** にチェック
3. 保存後、ダッシュボードにアクセスするとブラウザのパスワードダイアログが出る

### 6. 動作確認

```bash
# ローカル実行
cp .env.example .env
# .env を編集して各値を設定
pip install -e .
python -m src  # または python -m src.cli.main

# GitHub Actions から手動実行
# Actions タブ > Daily Tech Article Fetch > Run workflow
```

## 開発

```bash
pip install -e ".[dev]"

# テスト
pytest tests/ -v

# Lint
ruff check src/ tests/

# 型検査
mypy src/
```

## コスト

| サービス | 月間使用量 | コスト |
|----------|-----------|--------|
| GitHub Actions（パブリックリポジトリ） | 30回 × 約2分 | **$0** |
| LINE Messaging API（月200通無料） | 最大 150 通/月（5カテゴリ × 30日） | **$0** |
| Gemini API（無料枠: 1日1500リクエスト） | 150 リクエスト/月（5カテゴリ × 30日） | **$0** |
| Cloudflare Workers（無料枠: 10万リクエスト/日） | 30回 | **$0** |
| Cloudflare KV（無料枠: 10万読み取り/日） | 〜100回/日 | **$0** |
| Cloudflare Pages（無料枠: 500デプロイ/月） | 数回/月 | **$0** |
| **合計** | | **$0/月** |

---

## 記事ソース仕様

### RSS フィード（`src/config.py` > `RSS_SOURCES`）

| カテゴリ | ソース名 | RSS URL |
|---|---|---|
| 日本語技術記事 | Zenn | `https://zenn.dev/feed` |
| 日本語技術記事 | Qiita 人気記事 | `https://qiita.com/popular-items/feed` |
| 日本語技術記事 | はてブ IT | `https://b.hatena.ne.jp/hotentry/it.rss` |
| 日本語技術記事 | note テック | `https://note.com/hashtag/tech?format=rss` |
| 企業テックブログ | メルカリ | `https://engineering.mercari.com/blog/feed.xml` |
| 企業テックブログ | サイバーエージェント | `https://developers.cyberagent.co.jp/blog/feed/` |
| 企業テックブログ | DeNA | `https://engineering.dena.com/blog/index.xml` |
| 企業テックブログ | SmartHR | `https://tech.smarthr.jp/feed` |
| 企業テックブログ | LayerX | `https://tech.layerx.co.jp/feed` |
| 海外公式ブログ | GitHub Blog | `https://github.blog/feed/` |
| 海外公式ブログ | AWS Blog | `https://aws.amazon.com/blogs/aws/feed/` |
| 海外公式ブログ | Cloudflare Blog | `https://blog.cloudflare.com/rss/` |
| 海外公式ブログ | Vercel Blog | `https://vercel.com/blog/rss.xml` |

サムネイル画像を `media:thumbnail` / `media:content` / `enclosures` から自動抽出する。

### API 取得ソース

| ソース | 方式 | フィルタ条件 |
|---|---|---|
| Qiita | REST API | `stocks:>50`（一般）、`stocks:>10 tag:X`（タグ別 8 件並列） |
| dev.to | REST API | 過去 7 日間のトップ 20 件 |
| Hacker News | Firebase REST API | トップ 30 件中、スコア ≥ 100 かつ URL あり |
| Reddit | JSON API | 7 サブレディット hot posts、スコア ≥ 500、セルフポストを除外 |
| SpeakerDeck | Atom | 5 カテゴリ（programming / science / business / education / design）、CJK 文字を含む日本語スライドのみ |

Qiita タグ: `java`, `spring-boot`, `postgresql`, `typescript`, `react`, `nextjs`, `aws`, `agile`  
Reddit サブレディット: `java`, `SpringBoot`, `typescript`, `reactjs`, `nextjs`, `aws`, `agile`, `ExperiencedDevs`

---

## データモデル（`src/models.py`）

```python
class Article(BaseModel):
    title: str
    url: HttpUrl
    summary: str = ""
    source: str           # 例: "Zenn", "GitHub Blog", "Reddit r/java"
    published_at: datetime | None = None
    thumbnail_url: str | None = None

class SelectedArticle(BaseModel):
    article: Article
    reason: str           # 日本語 30 字以内
    category_id: str | None = None  # "backend" | "frontend" | "aws" | "management" | "others"

class ArticleFeedback(BaseModel):
    action: Literal["good", "bad"]
    title: str
    source: str
    url: str
    timestamp: datetime

class UserSettings(BaseModel):
    categories: dict[str, bool]      # カテゴリ ON/OFF（デフォルト全て True）
    sources_enabled: dict[str, bool] # ソース ON/OFF（空 dict は全 ON）
    max_per_category: int = 5        # カテゴリあたり最大選定数（1〜5）
    exclude_keywords: list[str] = [] # タイトル・サマリーにマッチしたら除外
    include_keywords: list[str] = [] # Gemini プロンプトに追加して優先

class UserPreferences(BaseModel):
    history: list[ArticleFeedback] = []
    def get_summary(self) -> str: ...  # good/bad 上位 3 ソースをマークダウンで返す
```

---

## カテゴリ分類（`src/selector/categorizer.py`）

キーワードマッチング（タイトル + サマリーに対してケースインセンシティブ）で 5 カテゴリに分類。  
マッチ優先順位: backend → frontend → aws → management → others。

| カテゴリ ID | 表示名 | 主なキーワード |
|---|---|---|
| `backend` | バックエンド | java, spring, kotlin, python, go, rust, postgresql, mysql, redis, api, microservice, ... |
| `frontend` | フロントエンド | typescript, javascript, react, vue, angular, nextjs, css, html, web, ... |
| `aws` | AWS・クラウド | aws, amazon, ec2, s3, lambda, cloud, kubernetes, docker, terraform, ... |
| `management` | 開発マネジメント | em, engineering manager, scrum, agile, 1on1, チーム, マネジメント, ... |
| `others` | その他 | （上記に非該当） |

Gemini に渡す前に各カテゴリを `published_at` 降順ソートし、最大 `GEMINI_MAX_INPUT_PER_CATEGORY`（25件）に切り詰める。

---

## Gemini 記事選定（`src/selector/gemini_selector.py`）

### モデル設定

| 設定 | 値 |
|---|---|
| プライマリモデル | `gemini-2.5-flash` |
| フォールバックモデル | `gemini-2.5-flash` |
| カテゴリ別最大選定数 | 5 件（`SELECT_MAX_PER_CATEGORY`） |
| 最大リトライ数 | 5 回（指数バックオフ、ベース 2 秒） |

### 処理フロー

5 カテゴリを `asyncio.gather()` で並列実行。各カテゴリに対して:
1. カテゴリ専用のシステムプロンプトを構築（選定観点・ユーザー嗜好サマリー・優先キーワードを含む）
2. 候補記事をナンバリングしたテキストとして渡す
3. Gemini が `[{"index": N, "reason": "理由"}]` 形式の JSON を返す
4. インデックスで元記事を参照し `SelectedArticle` に変換

選定件数は `UserSettings.max_per_category`（1〜5）で動的に変更される。

### システムプロンプト構成

```
あなたはWebエンジニア向けの技術記事キュレーターです。
{カテゴリ名} カテゴリの記事リストから {N} 件を選んでください。

選定基準:
- {カテゴリ別の観点（例: backend は Spring Boot, PostgreSQL を優先）}
- 話題性・新規性（リリース情報、アーキテクチャ刷新など）
- 学習価値の高さ（深い技術解説、設計思想の説明）
- 多様性（同一トピックの記事が重複しないよう調整）

除外基準:
- 宣伝・採用目的が主な記事
- 内容が浅い入門記事

出力形式: JSON配列のみ
[{"index": 0, "reason": "選定理由（日本語30字以内）"}, ...]

{ユーザーが関心あるキーワード（UserSettings.include_keywords が設定されている場合）}
{ユーザー嗜好サマリー（存在する場合）}
```

### エラーハンドリング

| 状況 | 挙動 |
|---|---|
| 日次クォータ枯渇（`PerDay` 検出） | フォールバックモデルに即切り替え |
| レート制限（429） | `Retry-After` ヘッダーを優先、指数バックオフで最大 5 回リトライ |
| 全モデル失敗 | そのカテゴリは空リストを返す（フォールバック選定なし） |

---

## LINE メッセージ仕様（`src/notifier/line_notifier.py`）

カテゴリごとに 1 メッセージ（Flex Message）を送信（最大 5 メッセージ/回）。  
記事番号はカテゴリをまたいでグローバルに 1 から連番（Webhook での KV 照合用）。

```
┌──────────────────────────────────────┐
│ 🗂️ バックエンド (2026/04/19)         │  ← ヘッダー
├──────────────────────────────────────┤
│ #1                              Zenn │  ← 記事番号（緑）＋ソース名（グレー）
│ [サムネイル画像]                      │  ← thumbnail_url がある場合のみ（20:13）
│ タイトル（太字）                      │
│ 選定理由（グレー小文字）               │
│ [👍 Good] [👎 Bad] [🔗 読む]         │  ← ボタン横並び
├──────────────────────────────────────┤
│ #2  ...                              │
└──────────────────────────────────────┘
```

- **👍 Good / 👎 Bad**: `MessageAction`（タップ時に `"👍N"` / `"👎N"` を LINE で送信）
- **🔗 読む**: `URIAction`（記事 URL を直接開く）
- `alt_text`（通知プレビュー）: `"🗂️ {カテゴリ名} — N 件"`

---

## ユーザー嗜好システム

### Cloudflare KV データ構造

**キー: `preferences`**
```json
{
  "history": [
    {
      "action": "good",
      "title": "TypeScript 5.5の新機能まとめ",
      "source": "Zenn",
      "url": "https://...",
      "timestamp": "2026-04-05T08:05:00Z"
    }
  ]
}
```
最大 100 件。超過時は古い順に削除。

**キー: `last_articles`**
```json
{
  "1": {"title": "...", "source": "Zenn", "url": "https://..."},
  "2": {"title": "...", "source": "GitHub Blog", "url": "https://..."}
}
```
グローバル連番（カテゴリをまたぐ）。毎回上書き。

**キー: `articles:YYYY-MM-DD`**
```json
[
  {
    "title": "...", "source": "Zenn", "url": "https://...",
    "category_id": "backend", "reason": "選定理由",
    "thumbnail_url": "https://...", "published_at": "2026-04-19T08:00:00+00:00"
  }
]
```
日別の配信履歴。最大 90 日保持し、古いキーは自動削除。

**キー: `article_index`**
```json
{"dates": ["2026-04-19", "2026-04-18", ...]}
```
配信日リスト（降順）。`articles:*` キーのインデックスとして使用。

**キー: `settings`**
```json
{
  "categories": {"backend": true, "frontend": false, ...},
  "sources_enabled": {"はてブIT": false},
  "max_per_category": 3,
  "exclude_keywords": ["入門", "ハンズオン"],
  "include_keywords": ["Rust", "LLM"]
}
```
ダッシュボードの設定フォームで編集。配信バッチ起動時に読み込まれる。

### Gemini への嗜好反映

`UserPreferences.get_summary()` で history を集計し、システムプロンプトに追記:
```
ユーザーの過去の評価傾向（参考情報）:
- 高評価したソース: Zenn (4件), GitHub Blog (2件)
- 低評価したソース: はてブIT (2件)

この傾向を参考にしつつ、多様性も維持してください。
```

ソース別の good/bad 集計（各上位 3 件）のみ。トピック集計は行わない。

---

## Cloudflare Worker 仕様（`cloudflare/src/index.js`）

1. `X-Line-Signature` ヘッダーで HMAC-SHA256 署名検証
2. `events[].message.text` から `/^([👍👎])(\d+)$/u` でパース
3. `KV.get("last_articles")` → 記事 N の情報を取得
4. `KV.get("preferences")` → 既存履歴を取得
5. フィードバックを追記（最大 100 件でローテート）
6. `KV.put("preferences", updatedData)` で保存
7. 200 OK を返す（正常時は返信しない、エラー時のみ返信）

### バインディング・環境変数

| 名前 | 種別 | 用途 |
|---|---|---|
| `LINE_CHANNEL_SECRET` | Secret | HMAC-SHA256 署名検証 |
| `LINE_CHANNEL_ACCESS_TOKEN` | Secret | エラー時の Reply API |
| `KV` | KV Namespace binding | 嗜好・記事リストの読み書き |

---

## Terraform IaC（`terraform/`）

### 管理リソース

| リソース | 内容 |
|---|---|
| `cloudflare_workers_kv_namespace` ("preferences") | KV Namespace 作成 |
| `cloudflare_workers_script` ("webhook") | Worker スクリプトのデプロイ |
| `cloudflare_pages_project` ("dashboard") | Pages プロジェクト作成（KV バインド共有） |

### 変数（`terraform/variables.tf`）

| 変数名 | Sensitive | 用途 |
|---|---|---|
| `cloudflare_api_token` | yes | Terraform 認証 |
| `cloudflare_account_id` | no | アカウント識別子 |
| `line_channel_secret` | yes | Worker Secret として設定 |
| `line_channel_access_token` | yes | Worker Secret として設定 |

### 出力

- `kv_namespace_id`: GitHub Secrets の `CLOUDFLARE_KV_NAMESPACE_ID` に登録
- `worker_url`: LINE Developers の Webhook URL に設定
- `dashboard_url`: ダッシュボードの URL（`https://tech-article-fetcher-dashboard.pages.dev`）

---

## GitHub Actions ワークフロー

### `daily-fetch.yml` — 記事収集・配信

```yaml
on:
  schedule:
    - cron: '0 23 * * *'  # JST 8:00 毎朝
  workflow_dispatch:        # 手動実行も可
```

### `dashboard-deploy.yml` — ダッシュボードデプロイ

`dashboard/` 配下の変更が `main` にプッシュされると自動で Cloudflare Pages にデプロイ。

### 必要な GitHub Secrets

| Secret 名 | 用途 |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API 認証 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Push 送信 |
| `LINE_USER_ID` | 送信先ユーザー ID |
| `LINE_CHANNEL_SECRET` | Webhook 署名検証 |
| `CLOUDFLARE_API_TOKEN` | KV REST API 認証・Pages デプロイ |
| `CLOUDFLARE_ACCOUNT_ID` | KV REST API・Pages デプロイ |
| `CLOUDFLARE_KV_NAMESPACE_ID` | KV Namespace 指定 |

---

## Web ダッシュボード（`dashboard/`）

Cloudflare Pages でホストされる管理 UI。Next.js 静的書き出し + Pages Functions で構成。UI プリミティブに Radix UI（Tooltip・Dialog）、スタイリングに Tailwind CSS v4 を使用。

### ページ構成

| パス | 内容 |
|---|---|
| `/` | ホーム — 今日の配信記事・高評価ソース Top3 |
| `/articles/` | 過去記事 — 日付フィルタで過去90日の配信を閲覧 |
| `/stats/` | 統計 — 週次フィードバック推移・ソース別評価・カテゴリ分布（Recharts） |
| `/settings/` | 設定 — カテゴリ/ソース ON/OFF・件数・除外/優先キーワードを編集。各操作の影響をツールチップ・プレビュー文・確認ダイアログで事前に提示。未保存変更インジケータと離脱警告付き |

### API（Pages Functions）

| エンドポイント | 説明 |
|---|---|
| `GET /api/articles?from=&to=` | 指定期間の日別配信記事を返す |
| `GET /api/stats` | フィードバック統計・週次トレンド・カテゴリ分布を返す |
| `GET /api/preferences` | 評価履歴（preferences KV）を返す |
| `GET /api/settings` | 現在の配信設定を返す |
| `PUT /api/settings` | 配信設定を更新する（次回配信バッチから反映） |

### 認証

`DASHBOARD_SECRET` 環境変数（Cloudflare Pages → Settings → Environment variables で設定）が存在する場合、HTTP Basic Auth でパスワードを要求する。

### 設定スキーマ v2

`PUT /api/settings` は v1 互換フィールドに加えて v2 フィールドを受け付ける。

```jsonc
{
  // v1 互換（既存フィールド）
  "categories": { "backend": true, "frontend": true, "aws": true, "management": true, "others": true },
  "sources_enabled": {},
  "max_per_category": 5,
  "exclude_keywords": [],
  "include_keywords": [],

  // v2 拡張（optional — 未設定時は fetcher が config.py のデフォルトを使用）
  "sources": [
    { "name": "Zenn", "type": "rss", "url": "https://zenn.dev/feed", "enabled": true },
    { "name": "Qiita:TypeScript", "type": "qiita", "params": { "tag": "TypeScript" }, "enabled": true },
    { "name": "SpeakerDeck:programming", "type": "speakerdeck", "params": { "category": "programming" }, "enabled": true }
  ],
  "category_defs": [
    { "id": "backend", "name": "バックエンド", "keywords": ["java", "spring"], "enabled": true, "order": 0 }
  ],
  "article_fetch_hours": 24,
  "gemini_max_input_per_category": 25,
  "schema_version": 2
}
```

v1 → v2 マイグレーションは自動。`PUT /api/settings` で `sources` または `category_defs` を含めると `schema_version: 2` に昇格する。既存の v1 フィールドはそのまま読み書きされる（後方互換）。

---

## エラーハンドリング方針

| 対象 | 失敗時の挙動 |
|---|---|
| 各フィード取得 | 独立して実行。一部失敗しても他で継続（`return_exceptions=True`） |
| Gemini API（クォータ枯渇） | フォールバックモデルに即切り替え |
| Gemini API（レート制限） | 指数バックオフで最大 5 回リトライ |
| Gemini API（全失敗） | そのカテゴリは空リストで継続（フォールバック選定なし） |
| Cloudflare KV 読み取り失敗 | 嗜好なしで通常通り実行 |
| Cloudflare KV 書き込み失敗 | ログ出力のみ、送信は継続 |
| 全体失敗 | Actions ジョブを失敗させ GitHub のメール通知で検知 |

---

## devContainer 仕様（`.devcontainer/`）

- ベースイメージ: `python:3.12-slim`
- 追加ツール: Node.js（Wrangler CLI 用）、Terraform CLI
- VS Code 拡張: `ms-python.python`, `ms-python.ruff`, `ms-python.mypy-type-checker`, `hashicorp.terraform`
- `postCreateCommand`: `pip install -e '.[dev]'`
