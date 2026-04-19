# UX改善計画: tech-article-fetcher

## Context
現在のLINEボットは記事の自動配信と👍/👎フィードバックのみ対応。
ユーザーは以下のことができない:
- 好みのトピックを自分で変更する（config.py にハードコード）
- 好きなタイミングで記事を取得する（毎朝8時固定）
- フィードバック統計を確認する

LINEチャットコマンドを追加することで、既存のインフラ（Cloudflare Worker + KV）を活かしてゼロコストで全問題を解決できる。

## 実装する機能（優先順）

### Tier 1: LINEコマンドルーター + トピック管理（最高優先度）
- `/help` — コマンド一覧表示
- `/topics` — 現在のトピック表示
- `/add <topic>` — トピック追加（例: `/add Rust`）
- `/remove <topic>` — トピック削除
- `/stats` — フィードバック統計表示

### Tier 2: オンデマンド記事取得
- `/fetch` — 今すぐ記事取得（GitHub repository_dispatch + 1時間クールダウン）

---

## KVストレージのスキーマ変更

### 新しいキー: `user_settings`
```json
{
  "topics": ["TypeScript", "React", "AWS", "Rust"],
  "disabled_sources": [],
  "fetch_cooldown_until": "2026-04-06T09:15:00Z"
}
```

`preferences` キー（既存）は変更なし。後方互換性を保つ。

トピックが未設定の場合は `config.py` の `PREFERRED_TOPICS` にフォールバック。

---

## 実装ステップ

### Step 1: Python — モデル・ストレージ追加
**`src/models.py`**
```python
class UserSettings(BaseModel):
    topics: list[str] = []
    disabled_sources: list[str] = []
    fetch_cooldown_until: datetime | None = None
```

**`src/storage/preferences.py`**
- `get_user_settings() -> UserSettings`
- `write_user_settings(settings: UserSettings) -> None`
- `get_effective_topics() -> list[str]` — KVのトピック（なければ config のデフォルト）

### Step 2: Python — パイプライン分離
トピックをモジュールレベル定数から関数引数に変更:
- `src/main.py` — `get_effective_topics()` を呼び、各フェッチャーに渡す
- `src/fetchers/qiita_fetcher.py` — `fetch_qiita(topics: list[str] | None = None)`
- `src/fetchers/reddit_fetcher.py` — `fetch_reddit(topics: list[str] | None = None)` + topic→subreddit マッピング辞書追加
- `src/selector/gemini_selector.py` — `select_articles(..., topics: list[str] | None = None)` でプロンプト動的生成

### Step 3: Cloudflare Worker — コマンドルーター追加
**`cloudflare/src/index.js`**

コマンドルーター（`/` で始まる場合にルーティング）:

| コマンド | 処理 |
|---|---|
| `/help` | 静的テキスト返信 |
| `/topics` | KV `user_settings.topics` 表示 |
| `/add <topic>` | KVに追加（最大15件） |
| `/remove <topic>` | KVから削除 |
| `/stats` | KV `preferences.history` 集計・表示 |
| `/fetch` | GitHub repository_dispatch 呼び出し |

**新規 Cloudflare Secrets:**
- `GITHUB_PAT` — `public_repo` スコープのPAT
- `GITHUB_REPO` — `owner/repo` 形式

### Step 4: GitHub Actions
**`.github/workflows/daily-fetch.yml`**
```yaml
on:
  schedule:
    - cron: "0 23 * * *"
  workflow_dispatch:
  repository_dispatch:
    types: [on-demand-fetch]
```

---

## ユーザー向けコマンドUX例

```
/topics
→ 現在のトピック (6件):
  TypeScript / React / AWS / Java / Spring Boot / Next.js

/add Rust
→ ✅ 「Rust」を追加しました！
  現在のトピック (7件):
  TypeScript / React / AWS / Java / Spring Boot / Next.js / Rust

/remove Java
→ ✅ 「Java」を削除しました。

/fetch
→ 記事取得を開始しました！数分後に届きます ✨
  (クールダウン中) → 次回は 10:15 以降に利用できます。

/stats
→ 📊 あなたの評価統計
  総評価数: 23件 (👍15 / 👎8)
  よく高評価するソース: Zenn (6件), GitHub Blog (3件)
  高評価キーワード: TypeScript, パフォーマンス, アーキテクチャ
```

---

## 変更対象ファイル（主要）

1. `cloudflare/src/index.js` — コマンドルーター・各ハンドラ（最大の変更）
2. `src/models.py` — `UserSettings` モデル追加
3. `src/storage/preferences.py` — `get_user_settings()`, `get_effective_topics()` 追加
4. `src/selector/gemini_selector.py` — topics引数化・動的プロンプト生成
5. `src/fetchers/qiita_fetcher.py` — topics引数化
6. `src/fetchers/reddit_fetcher.py` — topics引数化 + topic→subreddit マッピング
7. `src/main.py` — `get_effective_topics()` を使って各フェッチャーに渡す
8. `.github/workflows/daily-fetch.yml` — `repository_dispatch` トリガー追加

---

## 検証方法

1. `/help` → コマンド一覧が表示される
2. `/topics` → デフォルトトピックが表示される
3. `/add Rust` → トピック追加、表示される
4. `/fetch` → GitHub Actions が起動し、数分後にLINEに記事が届く
5. `/fetch`（1時間以内2回目） → クールダウンメッセージが表示される
6. `/stats` → 評価件数・ソース別集計が表示される
7. 翌朝の自動配信でRustが含まれた記事が届く

---

## 注意点・リスク

- **topic→subreddit マッピング**: 全トピックのsubredditが存在するとは限らない。マッピング辞書で対応、未マッチはスキップ
- **GitHub PAT 有効期限**: 最大1年。定期的な更新が必要
- **クールダウン**: 1時間制限でGemini API使用量を抑制（月最大750回 = 定期30回 + オンデマンド720回以内）
- **LINEメッセージ上限**: 5000文字。既存ロジックで制御済み
