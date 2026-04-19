# 大カテゴリ別記事ピック機能の実装計画 (plan-3)

## Context
- **現状**: `select_articles()` が全記事から 5〜7 件まとめて選定し、単一の Flex Message (`FlexBubble`) で LINE に送信している (`src/selector/gemini_selector.py:149`, `src/notifier/line_notifier.py:156`)。
- **問題**: バックエンド / フロントエンド / AWS / マネジメント系のバランスが保証されず、話題が偏る。1 バブルに最大 10 件縦並びで、視認性も限界がある。
- **ゴール**: 5 つの大カテゴリ（= バックエンド / フロントエンド / AWS / マネジメント・組織 / その他）ごとに最大 5 件選定し、カテゴリ別に分割した LINE メッセージで配信する。

---

## 大カテゴリ / 中カテゴリ定義（確定済）

| 大カテゴリ ID | 大カテゴリ名 | 中カテゴリ（マッチキーワード例） |
|---|---|---|
| `backend` | バックエンド | Java, Spring Boot, PostgreSQL |
| `frontend` | フロントエンド | React, Next.js, TypeScript |
| `aws` | AWS | AWS（+ Lambda / ECS / RDS 等のサービス名は [Q1] で確認） |
| `management` | マネジメント/組織 | Engineering Manager, EM, 組織論, リーダーシップ |
| `others` | その他 | 上記いずれにも該当しない記事の受け皿 |

※「スクラム/EM」→ **「マネジメント/組織」に改称**（ユーザー確認済）。スクラムは中カテゴリから除外。

---

## 設計方針（確定済の選択肢）
- **分類方式**: カテゴリごとに Gemini を呼び分ける（合計 5 回、**並列実行**）
- **入力上限**: 25 件/カテゴリ（現行 `GEMINI_MAX_INPUT_ARTICLES` と同じ値）
- **LINE UX**: カテゴリごとに `pushMessage` を 1 通ずつ、**合計最大 5 通を分割送信**
- **記事不足時**: カテゴリ内候補がゼロでもそのまま 0 件として扱う（不足を他カテゴリから補填しない）
- **その他カテゴリ**: 未分類記事用のバケットとして 5 つ目に追加

---

## アーキテクチャ

### ① カテゴリ定義 — `src/config.py`
`CATEGORIES` を追加し、既存の `PREFERRED_TOPICS` / `QIITA_TAGS` / `REDDIT_SUBREDDITS` は残して再利用。

```python
CATEGORIES: list[dict] = [
    {
        "id": "backend",
        "name": "バックエンド",
        "keywords": ["java", "spring", "springboot", "spring boot",
                     "postgres", "postgresql"],
    },
    {
        "id": "frontend",
        "name": "フロントエンド",
        "keywords": ["react", "next.js", "nextjs", "typescript"],
    },
    {
        "id": "aws",
        "name": "AWS",
        "keywords": ["aws", "lambda", "ecs", "eks", "s3", "rds",
                     "dynamodb", "cloudfront"],  # [Q1]
    },
    {
        "id": "management",
        "name": "マネジメント/組織",
        "keywords": ["engineering manager", "エンジニアリングマネージャー",
                     "em", "1on1", "組織", "リーダー",
                     "チームビルディング", "マネジメント"],
    },
    {"id": "others", "name": "その他", "keywords": []},
]

SELECT_MAX_PER_CATEGORY = 5
SELECT_MIN_PER_CATEGORY = 0
GEMINI_MAX_INPUT_PER_CATEGORY = 25  # 現行値を踏襲
```

既存の `SELECT_MIN` / `SELECT_MAX` は段階的に廃止（`_fallback_select` 側の参照も書き換え）。

### ② 記事の振り分け — 新規 `src/selector/categorizer.py`
- `classify(article: Article) -> str`
  - タイトル + サマリを小文字化してキーワード一致
  - 最初にマッチしたカテゴリ ID を返す（`CATEGORIES` リスト順で優先）
  - どれにもマッチしなければ `"others"`
- `bucket_articles(articles: list[Article]) -> dict[str, list[Article]]`
  - 重複排除済み記事を 5 つのバケットに振り分ける
  - バケット内は `published_at` 降順にソート
  - 各バケットを `GEMINI_MAX_INPUT_PER_CATEGORY` 件で切り詰め

### ③ Gemini 並列選定 — `src/selector/gemini_selector.py`
- 新規: `async def select_articles_by_category(buckets: dict[str, list[Article]], preferences: UserPreferences | None) -> dict[str, list[SelectedArticle]]`
  - `asyncio.gather()` で 5 カテゴリ分の Gemini 呼び出しを並列実行（例外は `return_exceptions=True` で握りつぶし、失敗カテゴリは `_fallback_select` に落とす）
  - 各カテゴリ用にシステムプロンプトを動的生成（`_build_system_prompt(category)` を新規関数化）
    - プロンプト内の「優先トピック」はそのカテゴリの中カテゴリに差し替え
    - `selected count = 0〜SELECT_MAX_PER_CATEGORY` に変更
  - 0 件カテゴリ（候補バケットが空）は即 `[]` を返して API 呼び出しスキップ
- 既存 `select_articles()` は互換のため残すか削除するかは [Q4]。`main.py` からは削除候補。
- `_call_gemini()` の `SELECT_MIN` / `SELECT_MAX` 参照を per-category パラメータ引数に変更。
- `_fallback_select()` もカテゴリ単位で動作するよう、`max_count` 引数を追加。

### ④ LINE カテゴリ別送信 — `src/notifier/line_notifier.py`
- `send_line_message()` を削除し、新規に:
  ```python
  async def send_category_messages(selections: dict[str, list[SelectedArticle]]) -> None
  ```
- 処理:
  1. `CATEGORIES` 順に走査し、0 件カテゴリはスキップ（0 件時の「該当なし」通知は出さない → [Q2]）
  2. カテゴリごとに `_build_category_flex_message(category, selected, global_offset)` で Flex Message を組み立てる
     - ヘッダー: `🗂️ {カテゴリ名} (YYYY/MM/DD)`
     - 記事ボックスは `_build_article_box()` を流用
  3. **記事インデックスはグローバル連番**（1..N）にし、Cloudflare Worker 側の既存 `last_articles` 参照ロジック（数値キー）を破壊しない
  4. 5 件の `pushMessage` を `asyncio.gather()` で並列送信（LINE API のレート制限を確認しつつ逐次化も検討 — [Q3]）
- フォールバック判定 (`_is_fallback`) はそのまま流用可能。

### ⑤ KV への last_articles 書き込み — `src/storage/preferences.py`
- 現行の `write_last_articles(list[SelectedArticle])` を `dict[str, list[SelectedArticle]]` も受けられるよう拡張、または呼び出し側で **フラット化** してから渡す（推奨）。
- フラット順序 = `CATEGORIES` 順 × カテゴリ内順（= LINE メッセージ内インデックスと一致）。
- 各エントリに `category_id` を追加して Worker が `/stats` で集計できるようにする（Worker 側の互換性維持のため `title/source/url` は従来通り）。

### ⑥ メインフロー — `src/main.py`
```python
buckets = bucket_articles(unique_articles)
selections = await select_articles_by_category(buckets, preferences=preferences)
await send_category_messages(selections)
await write_last_articles(selections)
```

### ⑦ モデル拡張 — `src/models.py`
`SelectedArticle` に `category_id: str | None = None` を追加（KV 書き出し・Worker での集計用）。

---

## 変更対象ファイル

| ファイル | 変更内容 |
|---|---|
| `src/config.py` | `CATEGORIES`, `SELECT_MAX_PER_CATEGORY` 等を追加 |
| `src/models.py` | `SelectedArticle.category_id` 追加 |
| `src/selector/categorizer.py` | 新規（分類ロジック） |
| `src/selector/gemini_selector.py` | `select_articles_by_category()` 追加、プロンプト動的化、fallback 引数化 |
| `src/notifier/line_notifier.py` | `send_category_messages()` に差し替え、グローバル連番インデックス |
| `src/storage/preferences.py` | `write_last_articles()` がカテゴリ付き辞書を受けられるよう拡張 |
| `src/main.py` | 呼び出し構造を `bucket → select → send → write` に更新 |
| `tests/test_selector.py` | カテゴライザ + per-category 選定のユニットテスト追加 |
| `tests/test_notifier.py` | 分割メッセージ組み立ての検証 |

---

## 検証方法

1. **ユニットテスト**: `pytest tests/` で全緑を確認
   - `categorizer.classify()` が Java/React/AWS/EM キーワードを正しく振り分ける
   - `bucket_articles()` が 25 件上限で切ること
   - グローバル連番インデックスが LINE メッセージ間で衝突しないこと
2. **統合テスト**: ローカル `.env` を用意して `python -m src.main` を実行
   - 5 通のメッセージが LINE に届く（0 件カテゴリはスキップされる）
   - 各カテゴリに最大 5 件含まれる
   - サムネイル・ボタン（👍/👎/読む）が表示される
   - 👍/👎 が Cloudflare Worker 経由で `preferences` に書き込まれる（既存機能の回帰なし）
3. **エラーパス**:
   - Gemini API をダミーエラーにしてフォールバックが働くことを確認
   - 全記事 0 件時に従来通り `sys.exit(1)` すること

---

## [Q] / [A] — 確認待ち項目

### [Q1] AWS カテゴリのキーワードに個別サービス名（Lambda / ECS / RDS など）を含めるか？
- 「AWS」だけだと RDS や Lambda の記事を `others` に取りこぼす可能性。
- ただし "lambda" は関数型言語記事や Python の lambda 式とも衝突しうる（例: "lambda calculus"）。
- 案 A: `aws` に AWS サービス名を網羅的に入れる（Lambda, ECS, EKS, S3, RDS, DynamoDB, CloudFront, Step Functions, IAM, VPC）
- 案 B: `aws` キーワードは "aws" / "amazon web services" のみに絞り、サービス名は入れない
- [A1]: B

### [Q2] 記事 0 件のカテゴリは LINE 送信をスキップするか、「本日該当なし」を通知するか？
- 案 A: スキップ（メッセージ数を減らせる / 通知疲れ軽減）← デフォルト想定
- 案 B: 「本日 {カテゴリ名} の該当記事はありません」を送信
- [A2]: a

### [Q3] Gemini / LINE の 5 並列送信は本当に 5 本同時で良いか？
- Gemini: 無料枠はレート考慮無視と確認済み（4 並列→実際は 5 並列）
- LINE: `pushMessage` は 1 秒間 100 リクエストまで OK なので並列化で問題なし。ただし順序が崩れると UX 悪化（バックエンドより先にフロントエンドが届く等）。
- 案 A: Gemini は並列、LINE 送信は `CATEGORIES` 順に逐次（順序担保）
- 案 B: LINE も並列（速い / 順序不定）
- [A3]: a

### [Q4] 既存の `select_articles()` / `send_line_message()` は削除してよいか？
- 現状 `main.py` 以外から呼ばれていない想定。削除で配線をシンプルに保ちたい。
- テストやローカル検証用に残すなら deprecation コメントを添える。
- [A4]: y

### [Q5] Gemini プロンプトは完全にカテゴリ別に書き分けるか？
- 案 A: テンプレートに「{カテゴリ名}関連の記事から〜」だけ差し込む軽量差分
- 案 B: カテゴリごとに選定観点を手書き（例: Backend は設計・パフォーマンス優先、Management は組織課題・ケーススタディ優先）
- [A5]: a

### [Q6] KV の `last_articles` にカテゴリ情報を含める必要はあるか？
- Cloudflare Worker の `/stats` やフィードバック分析をカテゴリ別に拡張する計画があるなら必要。
- そうでなければ既存構造（title/source/url のみ）を維持して影響範囲を最小化する方が安全。
- [A6]: 影響範囲を最小化

### [Q7] フォールバック (`_fallback_select`) もカテゴリごとに実行するか？
- 案 A: Gemini が落ちた時は該当カテゴリのみ recency ベースで 5 件補填
- 案 B: カテゴリ単位の fallback はせず、0 件扱い（実装シンプル）
- [A7]: b

### [Q8] 中カテゴリの粒度はこれで足りるか？
- 例: フロントエンドに Vue / Svelte / Tailwind CSS など追加する？
- バックエンドに Go / Rust / Kotlin / Python / Django 等を含めない方針で良いか？（ユーザーが Java + Spring Boot ユーザーと想定）
- [A8]: y

---

## 実装ステップ（確定後の作業順）
1. `src/config.py` に `CATEGORIES` と per-category 定数を追加
2. `src/selector/categorizer.py` 新規作成 + ユニットテスト
3. `src/models.py` に `category_id` 追加
4. `src/selector/gemini_selector.py` をカテゴリ対応に改修（既存関数と並行実装）
5. `src/notifier/line_notifier.py` を `send_category_messages()` に差し替え
6. `src/storage/preferences.py` の `write_last_articles()` を辞書対応に拡張
7. `src/main.py` を新フローに差し替え
8. `tests/` を更新してローカルで全緑確認
9. ローカル `.env` で `python -m src.main` を実行し、LINE 実機で 5 通受信を確認
