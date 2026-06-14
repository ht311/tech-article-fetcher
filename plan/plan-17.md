# ダッシュボードのサムネ改善：OGP画像取得 + Twitter風カード (plan-17)

## Context

**問題**: ダッシュボードのサムネが「default で意味のないこと」が多い。
原因は `thumbnail_url` の供給元が **RSS/Atom フィードのメタデータのみ**（`media:thumbnail` / `media:content` / `enclosure`）であること。
- `src/services/fetchers/rss_fetcher.py:27` `_extract_thumbnail()` — 多くのフィードはこれを持たないか、サイト共通のデフォルト画像（ロゴ等）を返す
- `src/services/fetchers/qiita_fetcher.py` — サムネ抽出が一切なく常に `None`
- `src/services/fetchers/speakerdeck_fetcher.py:55` — media_thumbnail のみ

**ゴール**: Twitter のリンクカードのように、記事ページ自身の `og:image` を取得して**記事固有の意味あるサムネ**を表示する。併せてダッシュボードのカードを Twitter 風レイアウトに刷新する。

**ユーザー確認済みの方針**:
- 取得対象 = **選定後の最終記事のみ**（全カテゴリ計20-30件程度。HTTP リクエストを最小化）
- 既存サムネがあっても **og:image を常に優先**（取れなければ既存を維持）
- ダッシュボードカードを **Twitter 風に刷新**

依存は揃っている: `beautifulsoup4>=4.15.0`, `httpx`（pyproject.toml に既存）。

---

## 設計方針

新規モジュール `src/services/fetchers/ogp_fetcher.py` を追加し、`Article` のリストを受け取って
各記事 URL を並列 GET → `og:image`（無ければ `twitter:image`）を抽出 → `thumbnail_url` を上書きする
enrichment ステップを `src/cli/main.py` のフロー（選定・ピン留め後、LINE 送信前）に挿入する。

選定後に enrich することで:
- LINE 通知（`line_notifier.py` の `FlexImage`）とダッシュボード（`article_history` KV）の**両方**に反映される
- HTTP リクエストが最終記事数（~25件）に限定される

---

## アーキテクチャ / データ構造

- `Article.thumbnail_url`（`src/core/models.py:16`）は既存のまま。型変更なし。
- `SelectedArticle.article.thumbnail_url` を in-place で書き換える（pydantic モデルなので属性代入で更新）。
- KV 書き込み（`preferences.py:201`）・API（`articles.ts`）・TS 型（`types.ts`）は既存のままで反映される。

---

## 実装ステップ

### Step 1: `src/services/fetchers/ogp_fetcher.py` — 新規作成 ✅ 完了
```python
async def _fetch_og_image(client, url) -> str | None:
    # GET → BeautifulSoup で <meta property="og:image"> content を取得
    # 無ければ <meta name="twitter:image"> / <meta property="og:image:url">
    # 相対URLは urljoin で絶対化。例外/タイムアウトは None
async def enrich_thumbnails(articles: list[Article]) -> None:
    # 並列 GET（httpx.AsyncClient, follow_redirects=True, timeout=10）
    # og:image が取れた記事のみ a.thumbnail_url を上書き
    # 同時実行数は asyncio.Semaphore(10) で制限
```

### Step 2: `src/cli/main.py` — enrichment 呼び出しを挿入 ✅ 完了
`_pin_important` 直後（line 238 の後）、`send_category_messages` の前に挿入:
```python
selected_articles = [s.article for arts in selections.values() for s in arts]
await enrich_thumbnails(selected_articles)
```

### Step 3: `dashboard/app/components/ArticleCard.tsx` — Twitter 風カードに刷新 ✅ 完了
- 縦型カード: 上部にワイドサムネ（`aspect-[1.91/1]`）、下部にタイトル/要約/source
- サムネ無し時は `categoryPlaceholderBg` プレースホルダを同じ比率で表示

### Step 4: `dashboard/app/components/CategorySection.tsx` — グリッド調整 ✅ 完了
```tsx
// 変更前
<div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
// 変更後
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
```

### Step 5: テスト（TDD: 8件全パス）✅ 完了
`tests/test_ogp_fetcher.py`
- og:image あり → 上書き
- 既存サムネも og:image で上書き（常に優先）
- twitter:image フォールバック
- og:image 無し → None のまま
- og:image 無し → 既存 thumbnail_url 維持
- 相対URL → 絶対化
- HTTP エラー → 既存維持（例外を投げない）
- 空リスト → 正常終了

---

## 残タスク

### Step 6: ダッシュボードのビルド確認・ブラウザ確認
- `pnpm install` → `pnpm build`（または `pnpm dev`）でビルド確認
- 実機でワイドサムネ表示・プレースホルダ・レスポンシブ列を目視確認
- ※ package.json の merge conflict が事前に解決済みであること

### Step 7: TypeScript 型チェック
- `pnpm typecheck`（`tsc --noEmit`）でエラーがないことを確認
- biome lint: `pnpm lint`

### Step 8: コミット・push・PR起票（commit-and-pr スキル使用）

---

## テスト方針

- `pytest tests/ -v` — 104 件全パス ✅
- `python -m ruff check src/ tests/` — クリア ✅
- `python -m mypy src/` — クリア ✅
- ダッシュボード: `pnpm dev` で起動 → ブラウザ確認（Step 6）

---

## 変更ファイル一覧

| ファイル | 状態 |
|---|---|
| `src/services/fetchers/ogp_fetcher.py` | 新規作成 |
| `src/cli/main.py` | 修正（import + enrich_thumbnails 呼び出し） |
| `dashboard/app/components/ArticleCard.tsx` | 修正（Twitter 風縦型カード） |
| `dashboard/app/components/CategorySection.tsx` | 修正（グリッド列数） |
| `tests/test_ogp_fetcher.py` | 新規作成（8件） |
