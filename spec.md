# tech-article-fetcher LINE ボット 仕様書

## したいこと

Webエンジニア向けの技術記事を毎日収集し、LINEに配信するボットを構築する。
GitHub Actions をスケジューラーとして使うことでサーバーレス・ゼロインフラコストを実現。
記事の選定は Gemini API に任せ、質の高いキュレーションを自動化する。
ユーザーは記事に対してgood/badを送ることで嗜好を記録し、日々の選定に反映される。

---

## アーキテクチャ概要

```
[GitHub Actions (cron: 毎日 JST 8:00)]
  ↓
Python スクリプト
  ├── 記事収集（RSS: 日本語・企業・海外公式ブログ / Qiita API タグ別並列取得）
  ├── 直近24時間にフィルタ・重複排除
  ├── Cloudflare KV からユーザー嗜好を読み込み
  ├── PREFERRED_TOPICS で上位25件にプリフィルタリング
  ├── Gemini API (gemini-2.0-flash → gemini-2.0-flash-lite フォールバック) で TOP 5〜7 件を選定
  ├── LINE Messaging API（Flex Message 縦並びカード・サムネイル付き）で送信
  └── 送信した記事リストを Cloudflare KV に書き込み

[Cloudflare Worker (常時稼働・無料)]
  ├── LINE webhookを受信・署名検証
  ├── 「👍1」「👎3」などのテキストをパース
  ├── KVの last_articles から記事情報を照合
  ├── KVの preferences に評価履歴を追記（最大100件）
  └── エラー時のみ返信（正常時は返信しない・メッセージ数節約）
```

---

## コスト分析

| サービス | 月間使用量 | コスト |
|---|---|---|
| GitHub Actions（パブリックリポジトリ） | 30回 × 約2分 | **$0** |
| LINE Messaging API（月200通無料） | 30通 | **$0** |
| Gemini API (gemini-2.0-flash) | ~2,000 tokens × 30回 | **$0（無料枠内）** |
| Cloudflare Workers（100k req/日無料） | 30回/日 | **$0** |
| Cloudflare KV（100k reads/日, 1k writes/日無料） | 60 ops/日 | **$0** |
| **合計** | | **$0/月** |

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
├── cloudflare/
│   └── src/
│       └── index.js             # LINE webhookハンドラー（Cloudflare Worker）
├── terraform/
│   ├── main.tf                  # Cloudflareプロバイダー設定・リソース定義
│   ├── variables.tf             # 変数定義
│   ├── outputs.tf               # KV Namespace IDなどの出力
│   └── terraform.tfvars.example # 変数サンプル
├── src/
│   ├── __init__.py
│   ├── main.py                  # エントリーポイント
│   ├── config.py                # ソース一覧・定数
│   ├── models.py                # Pydantic データモデル（Article.thumbnail_url含む）
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── rss_fetcher.py       # RSS/Atom フィード取得（サムネイル抽出対応）
│   │   ├── qiita_fetcher.py     # Qiita API 取得（タグ別並列取得対応）
│   │   └── devto_fetcher.py     # dev.to API 取得（サムネイル対応）
│   ├── selector/
│   │   ├── __init__.py
│   │   └── gemini_selector.py   # Gemini API による記事選定（嗜好反映・モデルフォールバック）
│   ├── notifier/
│   │   ├── __init__.py
│   │   └── line_notifier.py     # LINE Push（Flex Message 縦並びカード・サムネイル付き）
│   └── storage/
│       ├── __init__.py
│       └── preferences.py       # Cloudflare KV 読み書き
├── tests/
│   ├── test_fetchers.py
│   ├── test_selector.py
│   ├── test_notifier.py
│   └── test_preferences.py
├── .env.example
├── pyproject.toml
├── requirements.txt
└── spec.md
```

---

## 記事ソース一覧

### RSS フィード（`src/config.py`）

海外ソースは**公式企業ブログのみ**を対象とし、コミュニティ系（dev.to / Hacker News / Reddit）は除外。

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
| 海外公式ブログ | GitHub Blog | `https://github.blog/feed/` |
| 海外公式ブログ | AWS Blog | `https://aws.amazon.com/blogs/aws/feed/` |
| 海外公式ブログ | Cloudflare Blog | `https://blog.cloudflare.com/rss/` |
| 海外公式ブログ | Vercel Blog | `https://vercel.com/blog/rss.xml` |

RSS フィードからはサムネイル画像（`media:thumbnail` / `media:content` / `enclosures`）を自動抽出する。

### API取得

| ソース | 方式 | 備考 |
|---|---|---|
| Qiita | API | `stocks:>50` でフィルタ、トピックタグ別並列取得 |

---

## Gemini 記事選定ロジック（`src/selector/gemini_selector.py`）

使用モデル: `gemini-2.0-flash`（プライマリ）→ `gemini-2.0-flash-lite`（日次クォータ枯渇時フォールバック）

### プリフィルタリング

Gemini に渡す記事数を最大 `GEMINI_MAX_INPUT_ARTICLES`（デフォルト25件）に絞る。
`PREFERRED_TOPICS` のキーワードにマッチする記事を優先し、残りを直近記事で補う。

### System prompt

```
あなたはWebエンジニア向けの技術記事キュレーターです。
提供された記事リストから、以下の基準でおすすめ記事を5〜7件選んでください。

優先トピック（これらに関連する記事を積極的に選ぶ）:
Java、Spring Boot、PostgreSQL、TypeScript、React、Next.js、AWS、スクラム、Scrum、
エンジニアリングマネージャー、Engineering Manager

選定基準（優先順位順）:
1. 上記優先トピックに関連する実務で即役立つ記事
2. 話題性・新規性（リリース情報、アーキテクチャ刷新など）
3. 学習価値の高さ（深い技術解説、設計思想の説明）
4. 多様性（同一トピックの記事が重複しないよう調整）

除外基準:
- 宣伝・採用目的が主な記事
- 内容が浅い入門記事（初心者向けハンズオンなど）

出力形式: JSON配列のみ返してください。
[{"index": 0, "reason": "選定理由（日本語30字以内）"}, ...]
```

嗜好データがある場合、`UserPreferences.get_summary()` の結果をシステムプロンプトに追記する。

---

## LINE メッセージ仕様（`src/notifier/line_notifier.py`）

### メッセージ形式

単一 `FlexBubble`（size="giga"）内に記事カードを**縦並び**で最大10件表示。  
カード間には `FlexSeparator` を挿入。

各カードのレイアウト:

```
┌────────────────────────────┐
│ 📚 今日の技術記事 YYYY/MM/DD│  ← ヘッダー（フォールバック時は赤字＋警告）
├────────────────────────────┤
│ #1                    Zenn │  ← 記事番号（緑）＋ソース名
│ [サムネイル画像]            │  ← あれば表示（aspect_ratio="20:13"）
│ タイトル（太字）            │
│ 選定理由（グレー小文字）    │
│ [👍 Good] [👎 Bad] [🔗読む]│  ← 横並びボタン
├────────────────────────────┤
│ #2  ...                    │
└────────────────────────────┘
```

- **👍 Good / 👎 Bad**: `MessageAction` でタップ時に `👍N` / `👎N` を送信
- **🔗 読む**: `URIAction` で記事 URL を直接開く
- **サムネイル**: `Article.thumbnail_url` が存在する場合のみ表示
- **フォールバック時**: ヘッダーが赤色になり "⚠️ AI選定不可・最新順" を付記
- `alt_text`（通知文）: `📚 今日の技術記事 (YYYY/MM/DD) — N 件`

ユーザーがボタンをタップ → LINEがメッセージとして送信 → Cloudflare Worker が受信・KVに記録

---

## ユーザー嗜好システム

### データ構造（Cloudflare KV）

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

**キー: `last_articles`**
```json
{
  "1": {"title": "...", "source": "Zenn", "url": "https://..."},
  "2": {"title": "...", "source": "Hacker News", "url": "https://..."}
}
```

### Geminiへの嗜好反映

`UserPreferences.get_summary()` でhistoryを集計してGeminiプロンプトに追記:
```
ユーザーの過去の評価傾向（参考情報）:
- 高評価したソース: Zenn (4件), GitHub Blog (2件)
- 低評価したソース: はてブIT (2件)

この傾向を参考にしつつ、多様性も維持してください。
```

※ ソース別の good/bad 集計（各上位3件）。トピック集計は行わない。

---

## Cloudflare Worker 仕様（`cloudflare/src/index.js`）

### 処理フロー

1. `X-Line-Signature` ヘッダーでHMAC-SHA256署名検証
2. `events[].message.text` から `👍N` / `👎N` パターンをマッチ
3. `KV.get("last_articles")` → 記事Nの情報を取得
4. `KV.get("preferences")` → 既存履歴を取得
5. フィードバックを追記（最大100件でローテート）
6. `KV.put("preferences", updatedData)` で保存
7. 200 OK を返す（正常時は返信しない・エラー時のみ返信してメッセージ数を節約）

### 環境変数（Cloudflare Secrets）

| 変数名 | 内容 |
|---|---|
| `LINE_CHANNEL_SECRET` | LINE署名検証に使用 |

---

## Terraform IaC（`terraform/`）

Cloudflare Terraform プロバイダーでインフラをコード管理。

### 管理リソース

| リソース | 内容 |
|---|---|
| `cloudflare_workers_kv_namespace` | KV Namespace作成 |
| `cloudflare_workers_script` | Workerスクリプトのデプロイ |

### 変数（`terraform/variables.tf`）

| 変数名 | 内容 |
|---|---|
| `cloudflare_api_token` | Cloudflare APIトークン |
| `cloudflare_account_id` | CloudflareアカウントID |
| `line_channel_secret` | LINE署名検証キー（Workerのsecretとして設定） |

---

## devContainer 仕様（`.devcontainer/`）

- ベースイメージ: `python:3.12-slim`
- 追加ツール: Node.js（Wrangler CLI用）、Terraform CLI
- VS Code 拡張: `ms-python.python`, `ms-python.ruff`, `ms-python.mypy-type-checker`, `hashicorp.terraform`
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
| `LINE_CHANNEL_SECRET` | LINE署名検証キー |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API トークン |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare アカウント ID |
| `CLOUDFLARE_KV_NAMESPACE_ID` | KV Namespace ID（Terraform outputから取得） |

---

## エラーハンドリング方針

- 各フィード取得は独立して実行。一部失敗しても他で継続
- Gemini API エラー:
  - 429 日次クォータ枯渇（`PerDay` 検出）→ 即座に `gemini-2.0-flash-lite` へ切り替え
  - 429 分次レート制限 → API 指定の待機時間（`retryDelay`）で最大5回リトライ
  - 全モデル失敗時 → 直近記事の recency ベースフォールバック選定（LINE 通知に警告表示）
- Cloudflare KV 読み取り失敗: 嗜好なしで通常通り実行
- Cloudflare KV 書き込み失敗: ログ出力のみ、送信は継続
- 全体失敗時: Actions ジョブを失敗させ GitHub のメール通知で検知

---

## 前提条件（事前に用意するもの）

1. LINE Developers でチャンネル作成（Messaging API）
   - `LINE_CHANNEL_ACCESS_TOKEN` と `LINE_CHANNEL_SECRET` を取得
   - Webhook URLをCloudflare Worker URLに設定
2. ボットを友だち追加して `LINE_USER_ID` 取得
3. Google AI Studio で `GEMINI_API_KEY` 取得
4. Cloudflare アカウント作成（無料）
5. Terraform CLI インストール
6. `cd terraform && terraform init && terraform apply` でCloudflareリソース作成
7. GitHub リポジトリをパブリックに設定（Actions 無料化のため）
