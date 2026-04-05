# tech-article-fetcher LINE ボット 仕様書

## したいこと

Webエンジニア向けの技術記事を毎日収集し、LINEに配信するボットを構築する。
GitHub Actions をスケジューラーとして使うことでサーバーレス・ゼロインフラコストを実現。
記事の選定は Gemini API に任せ、質の高いキュレーションを自動化する。

---

## アーキテクチャ概要

```
GitHub Actions (cron: 毎日 JST 8:00)
  ↓
Python スクリプト
  ├── RSS/API から記事収集（Zenn, Qiita, 企業テックブログ 等 20+ ソース）
  ├── 直近24時間にフィルタ・重複排除
  ├── Gemini API (gemini-2.0-flash) で TOP 5〜7 件を選定
  └── LINE Messaging API (Push Message) でユーザーに送信
```

---

## コスト分析

| サービス | 月間使用量 | コスト |
|---|---|---|
| GitHub Actions（パブリックリポジトリ） | 30回 × 約2分 | **$0** |
| LINE Messaging API（月1000通無料） | 30通 | **$0** |
| Gemini API (gemini-2.0-flash) | ~2,000 tokens × 30回 | **$0（無料枠内）** |
| **合計** | | **$0/月** |

> Gemini API の無料枠は 1日1500リクエスト（Flash モデル）。完全ゼロコストで運用可能。

---

## ファイル構成

```
tech-article-fetcher/
├── .devcontainer/
│   ├── devcontainer.json
│   └── Dockerfile
├── .github/
│   └── workflows/
│       └── daily-fetch.yml
├── src/
│   ├── __init__.py
│   ├── main.py              # エントリーポイント
│   ├── config.py            # RSSソース一覧・定数（ここだけ編集すればソース追加可）
│   ├── models.py            # Pydantic データモデル（Article など）
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── rss_fetcher.py   # RSS/Atom フィード取得（feedparser）
│   │   └── qiita_fetcher.py # Qiita API 取得
│   ├── selector/
│   │   ├── __init__.py
│   │   └── gemini_selector.py  # Gemini API による記事選定
│   └── notifier/
│       ├── __init__.py
│       └── line_notifier.py    # LINE Flex Message 送信
├── .env.example
├── pyproject.toml
├── requirements.txt
└── spec.md                  # 本ファイル
```

---

## 記事ソース一覧（`src/config.py`）

RSS フィードで取得するソース（認証不要）:

| カテゴリ | ソース | RSS URL |
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
| 海外技術記事 | dev.to | `https://dev.to/feed` |
| 海外技術記事 | GitHub Blog | `https://github.blog/feed/` |
| 海外技術記事 | AWS Blog | `https://aws.amazon.com/blogs/aws/feed/` |
| 海外技術記事 | Cloudflare Blog | `https://blog.cloudflare.com/rss/` |
| 海外技術記事 | Vercel Blog | `https://vercel.com/blog/rss.xml` |

Qiita は API も使用（ストック数でスコアリング可能）:
- エンドポイント: `https://qiita.com/api/v2/items?query=stocks:>50&per_page=20`

---

## Gemini 記事選定ロジック（`src/selector/gemini_selector.py`）

使用モデル: `gemini-2.0-flash`（無料枠あり・高速）

### System prompt

```
あなたはWebエンジニア向けの技術記事キュレーターです。
提供された記事リストから、以下の基準でおすすめ記事を5〜7件選んでください。

選定基準（優先順位順）:
1. 実務で即役立つ技術トピック（新機能、ベストプラクティス、パフォーマンス改善）
2. 話題性・新規性（リリース情報、アーキテクチャ刷新など）
3. 学習価値の高さ（深い技術解説、設計思想の説明）
4. 多様性（同一トピックの記事が重複しないよう調整）

除外基準:
- 宣伝・採用目的が主な記事
- 内容が浅い入門記事（初心者向けハンズオンなど）

出力形式: JSON配列のみ返してください。
[{"index": 0, "reason": "選定理由（日本語30字以内）"}, ...]
```

---

## LINE メッセージ仕様（`src/notifier/line_notifier.py`）

Flex Message の carousel 形式で送信（1日1通カウント）:

```
📚 今日の技術記事 (2026/04/05)

1. [Zenn] タイトル
   → 選定理由
   🔗 URL

2. [GitHub Blog] タイトル
   → 選定理由
   🔗 URL
   ...
```

---

## devContainer 仕様（`.devcontainer/`）

- ベースイメージ: `python:3.12-slim`
- VS Code 拡張: `ms-python.python`, `ms-python.ruff`, `ms-python.mypy-type-checker`
- `postCreateCommand`: `pip install -e '.[dev]'`

---

## GitHub Actions ワークフロー仕様（`.github/workflows/daily-fetch.yml`）

```yaml
on:
  schedule:
    - cron: '0 23 * * *'   # JST 8:00 毎朝
  workflow_dispatch:         # 手動実行も可
```

### 必要な GitHub Secrets

| Secret 名 | 内容 |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio で発行した API キー |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE チャンネルアクセストークン（長期） |
| `LINE_USER_ID` | 送信先 LINE ユーザー ID（`U` で始まる文字列） |

---

## エラーハンドリング方針

- 各フィード取得は独立して実行。一部失敗しても他で継続
- Gemini API エラー: 最大3回リトライ（指数バックオフ）
- 全体失敗時: Actions ジョブを失敗させ GitHub のメール通知で検知

---

## 実装手順

1. devContainer セットアップ（`pyproject.toml`, `.devcontainer/`）
2. `src/models.py` + `src/config.py` でデータ構造・ソース一覧を定義
3. `src/fetchers/rss_fetcher.py` 実装・動作確認
4. `src/fetchers/qiita_fetcher.py` 実装
5. `src/selector/gemini_selector.py` 実装・プロンプト調整
6. `src/notifier/line_notifier.py` 実装・LINE 送信確認
7. `src/main.py` で統合・E2E テスト
8. GitHub Secrets 登録
9. `daily-fetch.yml` 追加、`workflow_dispatch` で動作確認 → cron 有効化

---

## 前提条件（事前に用意するもの）

1. LINE Developers でチャンネル作成 → `LINE_CHANNEL_ACCESS_TOKEN` 取得
2. ボットを友だち追加して `LINE_USER_ID` 取得
3. Google AI Studio で `GEMINI_API_KEY` 取得
4. GitHub リポジトリをパブリックに設定（Actions 無料化のため）
