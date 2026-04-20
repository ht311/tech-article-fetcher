# `python -m src` 実行ログの問題修正計画 (plan-9)

## Context

**現状**: ローカル実行 (`python -m src`) で以下4点の問題が出ている。
1. `Vercel Blog` が `404 Not Found` (`https://vercel.com/blog/rss.xml`)
2. `メルカリ` が `403 Forbidden` (`https://engineering.mercari.com/blog/feed.xml`)
3. `noteテック` が 200 OK だが `Fetched 0 articles` (`https://note.com/hashtag/tech?format=rss`)
4. **Qiita fetcher が全クエリ 200 OK なのに `Fetched 0 articles`** ← 本命のバグ

**ゴール**: これらを原因別に修正し、記事取得件数を回復する。特に Qiita は 8タグ + 人気記事で 1日数十件の安定供給源であり、現在 0 件は明らかな regression。

---

## 根本原因

### 原因1: Qiita fetcher のパース失敗 (最重要)

**該当**: `src/services/fetchers/qiita_fetcher.py:22`

```python
summary=item.get("body", "")[:300],
```

- Qiita API v2 の `GET /api/v2/items` は**認証トークン無しだと `body` フィールドが `null`（JSON の None）で返る**。
- `dict.get("body", "")` の第2引数はキーが**存在しない時のみ**適用される。キーが存在し値が `None` の場合は `None` が返り、`None[:300]` で `TypeError` が発生。
- `_parse_qiita_item` は `except Exception` で吸収して `None` を返す (L26–28) → 全 item が弾かれ 0 articles。
- 修正: `(item.get("body") or "")[:300]` とする（falsy 値もデフォルトに寄せる）。

### 原因2: 死んだ/ブロックされているソース

**該当**: `src/core/config.py` の `RSS_SOURCES`

| ソース | 行 | 症状 | 対応方針 |
|---|---|---|---|
| メルカリ | L12 | 403 Forbidden | User-Agent を付ければ回避できるケースが多い。まず UA 対応で再評価。 |
| Vercel Blog | L21 | 404 Not Found | Vercel は公式 RSS を停止済みと思われる。**削除**。 |
| noteテック | L10 | 200 OK だが 0 件 | UA 無し httpx は bot 判定されている可能性。UA 追加で再評価。 |

- `src/services/fetchers/rss_fetcher.py:84` の `httpx.AsyncClient` は User-Agent 未設定（httpx デフォルトの `python-httpx/x.y.z`）。
- 比較: `src/services/fetchers/speakerdeck_fetcher.py:23` は `Mozilla/5.0 (compatible; tech-article-fetcher/1.0)` を付与している。
- 対応: RSS fetcher にも同等の User-Agent ヘッダを追加。それでも 403/0 が残るソースのみ config から削除する。

### 原因3 (仕様確認): backend カテゴリが LINE 送信されていない

**該当**: `src/services/notifier/line_notifier.py:163-166`

```python
for cat in category_defs:
    selected = selections.get(cat.id, [])
    if not selected:
        continue
```

- `Bucket backend: 1 articles` だが Gemini が 0 件選択 → LINE スキップ。これは**設計どおり**（docstring にも「0件カテゴリはスキップする」と明記）。
- ログでも `category=backend` が無いのは期待挙動。今回の計画では**変更しない**。

---

## 実装ステップ

### Step 1: Qiita fetcher の `None` ガード修正
**ファイル**: `src/services/fetchers/qiita_fetcher.py:22`

- [ ] `summary=item.get("body", "")[:300]` → `summary=(item.get("body") or "")[:300]`
- [ ] 念のため `title` / `url` も `item["title"]` / `item["url"]` が `None` の場合を考慮するか検討（現在は `try/except` で吸収されるので必須ではない）。

### Step 2: RSS fetcher に User-Agent を追加
**ファイル**: `src/services/fetchers/rss_fetcher.py:84`

- [ ] `httpx.AsyncClient(follow_redirects=True)` → `httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (compatible; tech-article-fetcher/1.0)"})`
- [ ] 共通定数として `src/core/config.py` か `rss_fetcher.py` モジュールトップに `_USER_AGENT` を置くのが clean（speakerdeck_fetcher.py と揃える）。

### Step 3: 死んだソースの削除
**ファイル**: `src/core/config.py:5-22`

- [ ] Step 2 後に再実行して、以下の判定を行う:
  - Vercel Blog (L21): UA 付けても 404 なら**削除**
  - メルカリ (L12): UA 付けて 200 & 記事取得できれば残す、403 継続なら削除
  - noteテック (L10): UA 付けて記事が取れれば残す、0件継続なら削除
- [ ] KV 側の `settings` に過去のデフォルトが残っている場合、config.py 削除だけではランタイムから消えない (`src/core/runtime_config.py:17-24` の `_merge_with_defaults` で`enabled=True`で補完されるのは config 側に存在するソースのみなので、config から消せば新規ランタイムからは除外される)。ただし過去に KV `settings` に保存された名前一致ソースは残るため、必要なら dashboard から enabled=False を設定。

### Step 4: テスト
- [ ] `pytest tests/ -v` でリグレッションが無いことを確認。
- [ ] 既存の Qiita fetcher のテスト (`tests/services/fetchers/test_qiita_fetcher.py` 等) に `body=None` ケースがあるか確認し、無ければ追加。
- [ ] `ruff check src/ tests/` と `mypy src/` をパスさせる。

### Step 5: 動作確認
- [ ] `python -m src` を再実行し、Qiita が 0 件以上取得できることを確認。
- [ ] 削除対象ソースの Warning が消えていることを確認。

### Step 6: `plan/plan-9.md` への転記 (skill 規約)
- [ ] 承認後、この計画を `plan/plan-9.md` にも作成する（`/plan` skill は `plan/plan-{n}.md` を正本としている）。

---

## テスト方針

### 追加するユニットテスト
- `tests/services/fetchers/test_qiita_fetcher.py`
  - ケース: `item = {"title": "t", "url": "https://example.com", "body": None, "created_at": "2026-04-19T00:00:00+00:00"}` → `_parse_qiita_item` が `Article` を返す（現在の実装では `None` になるはず）。
  - ケース: `body` キーが存在しない場合も `summary=""` で `Article` を返す。

### 手動検証
- `python -m src` を実行して `Fetched N articles from Qiita` の `N` が 0 より大きいことを確認。
- Vercel/メルカリ/note の Warning が想定どおりになっているか確認。

---

## 不明点・確認事項

[Q1] **死んだソースの扱い**: Vercel Blog は公式 RSS を停止済みとの見立てで**削除**でよいか？ 代替 URL（例: `https://vercel.com/atom`）を調査してほしい場合は指示してほしい。

[A1] ok

[Q2] **メルカリ・note の UA 再評価**: Step 2 で UA 追加後、現場で再実行して判定する形でよいか？ （UA を付けても直らなかった場合、このターンで続けて削除まで実施してよいか）

[A2] ok

[Q3] **backend 通知の扱い**: Gemini が 0 件選んだカテゴリをスキップする現行仕様は維持でよいか？ それとも「バケットに記事があるなら最低1件は通知する」方針に変えたいか？ 後者は `gemini_selector.py` のプロンプト緩和 or `line_notifier.py` のスキップ削除が必要。

[A3] バケットに記事があるなら最低1件は通知する

[Q4] **KV 側の掃除**: config から削除したソースが KV `settings` に残っている場合、dashboard 経由で無効化する運用で良いか？ それとも自動削除ロジックを入れたいか？

[A4] dashboard更新時に勝手に消える

---

## 参考: 重要ファイル

- `src/services/fetchers/qiita_fetcher.py:13-28` `_parse_qiita_item`（Step 1 で修正）
- `src/services/fetchers/rss_fetcher.py:66-93` RSS fetch 本体（Step 2 で修正）
- `src/services/fetchers/speakerdeck_fetcher.py:23` User-Agent 参考実装
- `src/core/config.py:5-22` `RSS_SOURCES`（Step 3 で編集）
- `src/core/runtime_config.py:17-24` `_merge_with_defaults`（KV との合流ロジック）
- `src/services/notifier/line_notifier.py:163-166` 0件カテゴリスキップ仕様
