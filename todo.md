# tech-article-fetcher 実装TODO

spec.mdに基づく実装タスク一覧。毎日Webエンジニア向けに技術記事をキュレーションしてLINEに配信するボット。

---

## 完了済み（既存機能）

- [x] `pyproject.toml` の依存関係定義
- [x] `src/` ディレクトリ構成・`__init__.py`
- [x] `.env.example` 作成
- [x] `requirements.txt` 作成
- [x] `src/models.py`: `Article` / `SelectedArticle` モデル
- [x] `src/config.py`: RSSソース14件・Qiita設定・定数
- [x] `src/fetchers/rss_fetcher.py`: RSS並列取得・24hフィルタ
- [x] `src/fetchers/qiita_fetcher.py`: Qiita API取得
- [x] `src/selector/gemini_selector.py`: Gemini選定・リトライ・フォールバック
- [x] `src/notifier/line_notifier.py`: LINE Push送信
- [x] `src/main.py`: 全モジュール統合
- [x] `.github/workflows/daily-fetch.yml`: cronジョブ
- [x] `tests/test_fetchers.py` / `test_selector.py` / `test_notifier.py`

---

## Phase A: トレンド記事ソース追加

- [ ] `src/fetchers/hacker_news_fetcher.py` 実装
  - Firebase API `https://hacker-news.firebaseio.com/v0/topstories.json`
  - 上位30件を並列取得、スコア100以上・24h以内でフィルタ
  - `fetch_hacker_news() -> list[Article]`
- [ ] `src/fetchers/reddit_fetcher.py` 実装
  - `https://www.reddit.com/r/{subreddit}/hot.json?limit=25`
  - 対象: `programming`, `webdev`, `javascript`, `golang`, `MachineLearning`
  - User-Agentヘッダー設定、スコア500以上・24h以内でフィルタ
  - `fetch_reddit() -> list[Article]`
- [ ] `src/fetchers/devto_fetcher.py` 実装
  - `https://dev.to/api/articles?top=7&per_page=20`
  - `fetch_devto() -> list[Article]`
- [ ] `src/config.py` に HN / Reddit / dev.to 設定定数を追加
  - `HN_FETCH_COUNT = 30`, `HN_MIN_SCORE = 100`
  - `REDDIT_SUBREDDITS`, `REDDIT_MIN_SCORE = 500`
  - `DEVTO_API_URL`, `DEVTO_TOP_PERIOD = 7`
  - `MAX_ARTICLES_WITH_QUICKREPLY = 6`
- [ ] `src/main.py` に新フェッチャーを統合（`asyncio.gather` で並列実行）
- [ ] `tests/test_new_fetchers.py` 追加（HN・Reddit・dev.to）

---

## Phase B: ユーザー嗜好モデル・ストレージ

- [ ] `src/models.py` に `ArticleFeedback` / `UserPreferences` モデル追加
  - `ArticleFeedback`: `action (good|bad)`, `title`, `source`, `url`, `timestamp`
  - `UserPreferences`: `history: list[ArticleFeedback]`
  - `UserPreferences.get_summary() -> str` でGeminiプロンプト用サマリーを生成
- [ ] `src/storage/__init__.py` 作成
- [ ] `src/storage/preferences.py` 実装
  - `get_preferences() -> UserPreferences`: Cloudflare KV REST APIから取得
  - `write_last_articles(articles: list[SelectedArticle]) -> None`: 送信記事リストをKVに保存
  - 環境変数: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_KV_NAMESPACE_ID`
  - KV未設定時は空のPreferencesを返す（graceful degradation）
- [ ] `tests/test_preferences.py` 追加

---

## Phase C: Gemini選定に嗜好を反映

- [ ] `src/selector/gemini_selector.py` 修正
  - `select_articles(articles, preferences: UserPreferences | None = None)` に引数追加
  - `preferences` がある場合はシステムプロンプトに嗜好サマリーを追記
- [ ] `src/main.py` 修正
  - 記事送信前に `get_preferences()` を呼び出してGemini選定に渡す
  - 記事送信後に `write_last_articles()` でKVに記録

---

## Phase D: LINE Quick Reply 対応

- [ ] `src/notifier/line_notifier.py` 修正
  - `QuickReply` / `QuickReplyItem` / `MessageAction` をインポート
  - 記事リストを最大 `MAX_ARTICLES_WITH_QUICKREPLY = 6` 件に制限
  - `[👍1][👎1][👍2][👎2]...` のQuick Replyボタンを追加（最大12アイテム）
- [ ] `.env.example` に `LINE_CHANNEL_SECRET` を追記

---

## Phase E: Cloudflare Worker（LINE webhookハンドラー）

- [ ] `cloudflare/src/index.js` 実装
  - `X-Line-Signature` ヘッダーでHMAC-SHA256署名検証
  - `👍N` / `👎N` パターンのパース
  - `KV.get("last_articles")` で記事情報照合
  - `KV.get("preferences")` → フィードバック追記（最大100件）→ `KV.put()`
  - 200 OK を返す

---

## Phase F: Terraform IaC（Cloudflareインフラ）

- [ ] `terraform/variables.tf` 作成
  - `cloudflare_api_token`, `cloudflare_account_id`, `line_channel_secret`
- [ ] `terraform/main.tf` 作成
  - `cloudflare_workers_kv_namespace` リソース（KV Namespace作成）
  - `cloudflare_workers_script` リソース（Workerデプロイ、`cloudflare/src/index.js` を参照）
  - Workerのsecret bindingで `LINE_CHANNEL_SECRET` を設定
- [ ] `terraform/outputs.tf` 作成
  - `kv_namespace_id` を出力（GitHub Secretsに登録するため）
- [ ] `terraform/terraform.tfvars.example` 作成
- [ ] `.devcontainer/devcontainer.json` に Terraform CLI インストール追加
- [ ] ローカルで `terraform init && terraform plan` 動作確認

---

## Phase G: GitHub Actions 更新

- [ ] `.github/workflows/daily-fetch.yml` に新規 Secrets を追加
  - `LINE_CHANNEL_SECRET`
  - `CLOUDFLARE_API_TOKEN`
  - `CLOUDFLARE_ACCOUNT_ID`
  - `CLOUDFLARE_KV_NAMESPACE_ID`

---

## 環境変数一覧（最終）

| 変数名 | 取得元 | 用途 |
|--------|--------|------|
| `GEMINI_API_KEY` | Google AI Studio | Gemini API認証 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers | LINE Push送信 |
| `LINE_USER_ID` | LINE Developers | 送信先ユーザーID |
| `LINE_CHANNEL_SECRET` | LINE Developers | webhook署名検証 |
| `CLOUDFLARE_API_TOKEN` | Cloudflare Dashboard | KV REST API認証 |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Dashboard | KV REST API |
| `CLOUDFLARE_KV_NAMESPACE_ID` | `terraform output` | KV操作対象 |

---

## セットアップ手順（手動作業）

1. `.env` ファイルにAPIキーを設定（`.env.example` を参考）
2. `cd terraform && terraform init && terraform apply` でCloudflareリソース作成
3. `terraform output kv_namespace_id` の値をGitHub Secretsに登録
4. Cloudflare Worker URLをLINE DevelopersのWebhook URLに設定
5. GitHub Repository Secretsに全7変数を登録
6. `python -m src.main` でローカル実行確認
7. `pytest tests/` でテスト実行
8. GitHub Actions の `workflow_dispatch` で手動実行して動作確認
