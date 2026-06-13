# メジャーカンファレンス・Java専門・重要リリース情報の取りこぼし防止 (plan-12)

## Context

- **きっかけ**: 先日 JJUG があったが Java 記事が少なく、JAWS・Devsumi・TSKaigi のようなメジャーカンファレンスのスライドも日々の配信から漏れている。Java 26 のような重要リリース情報も確実に共有されない。
- **現状の構造的問題**:
  1. **Java が埋もれる**: Java は `backend` バケットで Spring/PostgreSQL と枠を奪い合う。InfoQ Java・Inside.java(OpenJDK公式) のような権威ある Java 専門ソースが未登録（`src/core/config.py:5-21`）。
  2. **カンファスライドが拾えない**: `speakerdeck_fetcher.py` は汎用5カテゴリの Atom を**日本語限定・24時間ウィンドウ**で取得するだけ。カンファ名軸の収集手段がなく、SpeakerDeck はタグ/検索の Atom を持たず、Docswell に公開RSSもない（Web調査で確認済み）。
  3. **重要ニュースが落ちる**: 24時間ウィンドウ＋Gemini選定で、リリース告知が候補から消える/選定で落ちる。「必ず配信する」ピン留め機構がない。アップロードが遅れる記事は 24h を外れる。
- **ゴール**:
  - Java 専門ソースを追加し Java の露出を底上げ。
  - **週次 GitHub Actions が Gemini の Web グラウンディングで「今メジャーなカンファレンス名」を発見し、KV のリストへどんどん追記**。日次fetchがそのリストでスライドを検索収集する（リストが育つ）。
  - 重要ソース（Java専門・カンファスライド）は**取得期間を延長**し、選定で**ピン留め**して確実に配信。延長による再送は送信済み履歴 dedup で防ぐ。

---

## 設計判断（確定済み）

| 論点 | 決定 |
|------|------|
| Java 強化 | Java 専門 RSS ソース追加（Inside.java Atom + InfoQ Java RSS。両方フィード有効性を確認済み・JDK26記事あり） |
| カンファ収集 | **週次ジョブが Gemini で発見 → KV リストへ追記。日次fetchがリストでSpeakerDeck検索+Docswell検索** |
| リスト保存先 | Cloudflare KV（新規キー `conferences`） |
| 発見手段 | Gemini の Google 検索グラウンディング（`google_search` tool） |
| 重要ニュース | 重要ソース＋ピン留め（カテゴリ内で重要記事を1件以上必ず確保） |
| 取得期間 | 重要ソースのみ延長（`EXTENDED_FETCH_HOURS=168` 想定）、通常は24h維持 |
| 再送防止 | KV 送信済み履歴から直近URLを読み、重複を除外 |

---

## アーキテクチャ / データ構造変更

### 1. 新しい KV キー（`src/core/kv_keys.py`）
```python
KV_CONFERENCES = "conferences"
```
dashboard 側 `_kv_keys.ts` にも対応追加（コントラクト同期）。

### 2. モデル（`src/core/models.py`）
- `Article` に `is_important: bool = False` を追加（ピン留め＆延長ウィンドウ対象の印。Article は TS 生成 EXCLUDE のため TS 影響なし）。
- `SourceDef.type` の Literal に `"docswell"` を追加。`SourceDef` に `important: bool = False` を追加（延長ウィンドウ対象マーク）。→ **`scripts/gen_types.py` で TS 型再生成が必須**（CI のドリフト検出に引っかかるため）。
- 新規 `ConferenceList`（KV `conferences` 用）:
  ```python
  class Conference(BaseModel):
      name: str            # 検索クエリに使う名称（例 "JJUG CCC", "JAWS DAYS", "TSKaigi"）
      added_at: datetime
      last_seen_at: datetime | None = None
  class ConferenceList(BaseModel):
      conferences: list[Conference] = []
  ```

### 3. config（`src/core/config.py`）
- `RSS_SOURCES` に Java 専門を追記し `important: True` 相当で扱う:
  - `{"name": "Inside.java", "url": "https://inside.java/feed.xml"}`
  - `{"name": "InfoQ Java", "url": "https://feed.infoq.com/java/"}`
- `default_sources()` でこの2つに `important=True` を立てる（他は False）。
- 追加定数:
  ```python
  EXTENDED_FETCH_HOURS = 168          # 重要ソースの取得ウィンドウ（7日）
  MAX_PINNED_PER_CATEGORY = 2         # カテゴリ毎にピン確保する重要記事上限
  SENT_HISTORY_DEDUP_DAYS = 7         # 再送防止で遡る送信済み履歴の日数
  CONFERENCE_SEARCH_HOURS = 168       # カンファスライドの収集ウィンドウ
  ```
- `backend` カテゴリの keywords に `"jdk"`, `"openjdk"` を追加（Java記事の取りこぼし減）。

---

## 実装ステップ

### Step 1: コントラクト層（モデル・KVキー・型再生成）
[ ] `kv_keys.py` に `KV_CONFERENCES`、`_kv_keys.ts` に対応追加
[ ] `models.py`: `Article.is_important`、`SourceDef.important`、`SourceDef.type` に `"docswell"`、`Conference`/`ConferenceList` 追加
[ ] `python scripts/gen_types.py` で `_types.generated.ts` 再生成（CIドリフト検出対策）

### Step 2: Java 専門ソース追加（`src/core/config.py`）
[ ] `RSS_SOURCES` に Inside.java / InfoQ Java を追加
[ ] `default_sources()` で該当2件に `important=True`
[ ] `backend` keywords に `jdk`/`openjdk`、定数群を追加

### Step 3: カンファレンスリストの永続化（`src/services/storage/`）
[ ] `preferences.py`（or 新規 `conferences.py`）に `get_conferences()` / `write_conferences()` を追加。既存KVヘルパー（`_kv_base_url`/`_auth_headers`）を再利用
[ ] 送信済みURL取得 `get_recent_sent_urls(days)` を追加: `KV_ARTICLE_INDEX` から直近日付を引き、`articles:<date>` を読んで URL 集合を返す

### Step 4: 週次カンファ発見ジョブ（新規）
[ ] `src/cli/update_conferences.py`（新エントリポイント）:
  - 既存 `genai.Client` を使い、`google.genai.types` の Google 検索グラウンディング（`tools=[Tool(google_search=GoogleSearch())]`）で「直近〜今後3ヶ月に開催される日本の主要技術カンファレンス名」を取得
  - 既存リストとマージ（名称の正規化で重複排除・append-only、`last_seen_at` 更新）
  - `write_conferences()` で KV 保存
[ ] `src/__main__.py` 相当の起動 or `python -m src.cli.update_conferences` で動く形に
[ ] `.github/workflows/weekly-conferences.yml`: `daily-fetch.yml` を雛形に、`cron: "0 0 * * 1"`（JST月曜9:00）、`GEMINI_API_KEY`+CLOUDFLARE系 env、`run: python -m src.cli.update_conferences`

### Step 5: カンファ/Docswell スライドフェッチャー（新規）
[ ] `src/services/fetchers/conference_fetcher.py`:
  - 引数: `conferences: list[Conference]`, `hours: int`
  - 各カンファ名で **SpeakerDeck 検索HTML** (`https://speakerdeck.com/search?q=<name>`) をパース（`feedparser`不可のため `httpx`+簡易HTMLパース。slideのtitle/url/著者/日付を抽出）
  - **Docswell** `https://www.docswell.com/search?key=<name>`（または /trending）をパースして該当スライド取得
  - 取得記事は `is_important=True`、`source="Conference:<name>"`、`CONFERENCE_SEARCH_HOURS` で時間フィルタ
  - 例外時は空リスト（既存フェッチャーの graceful 方針に合わせる）
[ ] HTML 構造はテストで mock 固定（実HTML依存を最小化）

### Step 6: SpeakerDeck 日本語限定の緩和（`speakerdeck_fetcher.py`）
[ ] 既存カテゴリフィードで、`PREFERRED_TOPICS` に関連するタイトルは日本語でなくても通すようフィルタ条件を拡張（`_is_japanese` or トピックマッチ）

### Step 7: 取得期間延長と統合（`src/cli/main.py`）
[ ] KV から `conferences` を読み込み
[ ] フェッチを「通常24h」と「重要=延長(168h)」に分離:
  - `important` ソースの RSS は `EXTENDED_FETCH_HOURS` で取得
  - `conference_fetcher` を `CONFERENCE_SEARCH_HOURS` で実行
[ ] フェッチ結果マージ後、`get_recent_sent_urls(SENT_HISTORY_DEDUP_DAYS)` で**送信済みURLを除外**（延長による再送防止）。`deduplicate()` の後段に追加

### Step 8: ピン留め選定（`src/services/selector/gemini_selector.py`）
[ ] `select_articles_by_category` 後処理で、各カテゴリの候補のうち `is_important=True` でGeminiに選ばれなかった記事を、`published_at`新しい順に最大 `MAX_PINNED_PER_CATEGORY` 件、選定結果の先頭へ強制挿入（重複回避）
[ ] ピン記事の `reason` は `"重要: <ソース名>"` などで明示

---

## テスト方針（TDD: Red→Green）

- `tests/` に以下を追加:
  - `test_config`: Java専門ソースが `important=True` で `default_sources()` に含まれる
  - `test_conferences_storage`: `get/write_conferences` の round-trip、append-only マージ（重複名は増えない・last_seen更新）
  - `test_conference_fetcher`: 固定HTML(SpeakerDeck検索/Docswell)をmockし、title/url/日付抽出・時間フィルタ・`is_important`付与を検証
  - `test_sent_history_dedup`: `get_recent_sent_urls` がindex+日別履歴からURL集合を返す（httpx mock）
  - `test_pin_selection`: Geminiが落とした重要記事がカテゴリ先頭にピンされる／上限を超えない
  - `test_speakerdeck`: 緩和後、PREFERRED_TOPICS一致の英語スライドが通る
- 既存テストの回帰確認: `pytest tests/ -v`、`ruff check src/ tests/`、`mypy src/`

---

## 検証（エンドツーエンド）

1. **週次ジョブ単体**: `python -m src.cli.update_conferences`（`.env`にGEMINI/CLOUDFLARE設定）→ KV `conferences` に名称が追記されるのを dashboard or KV で確認
2. **日次fetch**: `python -m src` → ログで「Conference: N slides」「important sources extended window」「filtered M already-sent」「pinned K articles」が出ることを確認
3. 型ドリフト: `python scripts/gen_types.py` 後に `git diff` がCIと一致（差分が出ない状態でコミット）
4. README のアーキテクチャ記述（`README.md:15-53`）に、週次カンファ発見ジョブ・Java専門ソース・重要ソース延長/ピンを追記（doc-sync）

---

## 不明点・確認事項

[Q1] カンファスライドはどのカテゴリで配信する？ 案: キーワードで通常バケット分け（Javaカンファ→backend等）し、ピン留めで確保。専用「カンファ」カテゴリは新設しない想定でよいか。
[A1]

[Q2] 週次ジョブが追加するカンファは「日本の技術カンファ」に限定でよいか（海外カンファ KubeCon/re:Invent 等も含めるか）。
[A2]

[Q3] Docswell/SpeakerDeck の検索HTMLスクレイピングは構造変更で壊れ得る。壊れた場合はログ警告＋スキップ（収集ゼロ）で許容してよいか（フェイルセーフ方針）。
[A3]

[Q4] 重要ソースの延長ウィンドウは 7日(168h) でよいか。カンファは開催後アップロードが遅れるため、もっと長く（14日）したい場合は要指定。
[A4]
