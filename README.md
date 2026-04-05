# tech-article-fetcher

Webエンジニア向けの技術記事を毎日自動収集し、LINEに配信するボット。  
GitHub Actions をスケジューラーとして使うことで **サーバーレス・ゼロインフラコスト** を実現。

## アーキテクチャ

```
GitHub Actions (cron: 毎日 JST 8:00)
  ↓
Python スクリプト
  ├── RSS / Qiita API から記事収集（14 RSS ソース + Qiita API）
  ├── 直近 24 時間にフィルタ・重複排除
  ├── Gemini API (gemini-2.0-flash) で TOP 5〜7 件を選定
  └── LINE Messaging API (Push Message) でユーザーに送信
```

## セットアップ

### 1. 必要なもの

| 項目 | 取得元 |
|------|--------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers コンソール > Messaging API |
| `LINE_USER_ID` | ボットを友だち追加後に取得（`U` で始まる文字列）|

### 2. ローカル実行

```bash
# 依存関係インストール
pip install -e .

# 環境変数を設定
cp .env.example .env
# .env を編集して各 API キーを記入

# 実行
python -m src.main
```

### 3. GitHub Actions のセットアップ

リポジトリの **Settings > Secrets and variables > Actions** に以下を登録：

- `GEMINI_API_KEY`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_USER_ID`

登録後、Actions タブから `Daily Tech Article Fetch` ワークフローを手動実行（`workflow_dispatch`）して動作確認できます。  
問題なければ毎朝 8:00 JST に自動実行されます。

## ファイル構成

```
src/
├── main.py              # エントリポイント
├── config.py            # RSSソース一覧・定数（ここを編集してソースを追加可能）
├── models.py            # Pydantic データモデル
├── fetchers/
│   ├── rss_fetcher.py   # RSS/Atom フィード並列取得
│   └── qiita_fetcher.py # Qiita API 取得
├── selector/
│   └── gemini_selector.py  # Gemini API による記事選定
└── notifier/
    └── line_notifier.py    # LINE Push Message 送信
.github/workflows/
└── daily-fetch.yml      # GitHub Actions ワークフロー
```

## 開発

```bash
# 開発用依存関係を含めてインストール
pip install -e ".[dev]"

# テスト実行
pytest tests/ -v

# Lint
ruff check src/ tests/
```

## コスト

| サービス | 月間使用量 | コスト |
|----------|-----------|--------|
| GitHub Actions（パブリックリポジトリ） | 30回 × 約2分 | **$0** |
| LINE Messaging API（月1000通無料） | 30通 | **$0** |
| Gemini API（無料枠: 1日1500リクエスト） | 30回 | **$0** |
| **合計** | | **$0/月** |
