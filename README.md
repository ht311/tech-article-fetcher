# tech-article-fetcher

Webエンジニア向けの技術記事を毎日自動収集し、LINEに配信するボット。  
GitHub Actions をスケジューラーとして使うことで **サーバーレス・ゼロインフラコスト** を実現。  
👍/👎 のフィードバックを学習し、日々の選定精度を向上させます。

## アーキテクチャ

```
GitHub Actions (cron: 毎日 JST 8:00)
  ↓
Python スクリプト
  ├── RSS / Qiita / Hacker News / Reddit / dev.to から記事並列収集
  ├── 直近 24 時間にフィルタ・重複排除
  ├── Cloudflare KV からユーザー嗜好（過去フィードバック）を読み込み
  ├── Gemini API (gemini-2.0-flash) で TOP 5〜7 件を選定（嗜好を反映）
  ├── LINE Messaging API（Flex Message カルーセル）で送信
  └── 送信記事リストを Cloudflare KV に保存

LINE アプリ (ユーザー)
  └── カード上の 👍/👎 ボタンをタップ
        ↓
  Cloudflare Worker（LINE Webhook ハンドラー）
  ├── X-Line-Signature で HMAC-SHA256 署名検証
  ├── KV.get("last_articles") で記事照合
  ├── KV.put("preferences") にフィードバック追記（最大 100 件）
  └── エラー時のみ返信（メッセージ数節約）
```

## ファイル構成

```
src/
├── main.py                      # エントリポイント
├── config.py                    # ソース一覧・定数
├── models.py                    # Pydantic データモデル
├── fetchers/
│   ├── rss_fetcher.py           # RSS/Atom フィード並列取得
│   ├── qiita_fetcher.py         # Qiita API 取得
│   ├── hacker_news_fetcher.py   # Hacker News Firebase API 取得
│   ├── reddit_fetcher.py        # Reddit API 取得
│   └── devto_fetcher.py         # dev.to API 取得
├── selector/
│   └── gemini_selector.py       # Gemini API による記事選定
├── notifier/
│   └── line_notifier.py         # LINE Push Message 送信（Flex Message カルーセル）
└── storage/
    └── preferences.py           # Cloudflare KV 読み書き（嗜好・記事リスト）
cloudflare/
└── src/index.js                 # Cloudflare Worker（LINE Webhook ハンドラー）
terraform/
├── main.tf                      # KV Namespace + Worker スクリプトのデプロイ
├── variables.tf
├── outputs.tf
└── terraform.tfvars.example
.github/workflows/
└── daily-fetch.yml              # GitHub Actions ワークフロー
```

## セットアップ

### 1. 必要なもの

| 変数名 | 取得元 | 用途 |
|--------|--------|------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) | 記事選定 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers > Messaging API | LINE Push 送信 |
| `LINE_USER_ID` | ボットを友だち追加後に取得（`U` で始まる文字列） | 送信先 |
| `LINE_CHANNEL_SECRET` | LINE Developers > チャンネル基本設定 | Webhook 署名検証 |
| `CLOUDFLARE_API_TOKEN` | [Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens) | KV REST API 認証 |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Dashboard の URL | KV REST API |
| `CLOUDFLARE_KV_NAMESPACE_ID` | `terraform output kv_namespace_id` | KV 操作対象 |

Cloudflare API トークンに必要な権限: **Workers KV Storage: Edit**, **Workers Scripts: Edit**

### 2. Cloudflare リソースを作成（Terraform）

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars を編集して各値を設定

terraform init
terraform apply -auto-approve

# KV Namespace ID を控える（GitHub Secrets に登録する）
terraform output kv_namespace_id
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

### 5. 動作確認

```bash
# ローカル実行
cp .env.example .env
# .env を編集して各値を設定
pip install -e .
python -m src.main

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
```

## コスト

| サービス | 月間使用量 | コスト |
|----------|-----------|--------|
| GitHub Actions（パブリックリポジトリ） | 30回 × 約2分 | **$0** |
| LINE Messaging API（月200通無料） | 30通 | **$0** |
| Gemini API（無料枠: 1日1500リクエスト） | 30回 | **$0** |
| Cloudflare Workers（無料枠: 10万リクエスト/日） | 30回 | **$0** |
| Cloudflare KV（無料枠: 10万読み取り/日） | 60回 | **$0** |
| **合計** | | **$0/月** |
