# 選定精度・嗜好学習の高度化（embedding 基盤）実装計画 (plan-16)

## Context

- **現状**:
  - 重複排除は **URL 完全一致のみ**（`src/services/selector/gemini_selector.py:83` `deduplicate()`）。同じニュース・同じトピックを別ソース（例: 公式ブログ + Zenn 解説 + はてブ）が配信すると、すべて Gemini 候補に残り、ノイズになる。
  - 嗜好学習は **キーワード部分一致のみ**（`src/core/models.py:91` `UserPreferences.get_summary()`）。good/bad のソース集計＋既知トピック語彙とのタイトル部分一致を、テキストサマリーとして Gemini プロンプトに注入しているだけ。語彙に無い概念（言い換え・新語）を捉えられない。
  - Gemini 入力前の切り詰めは **published_at 降順のみ**（`src/services/selector/categorizer.py:34` `bucket_articles()`）。`gemini_max_input_per_category`（25件）で切るため、ユーザー好みの記事が新しさ順で落ちることがある。
- **問題**: 配信のノイズ（重複トピック）と、嗜好反映の浅さ（キーワードマッチの限界）。
- **ゴール**: Gemini embedding を共通基盤として導入し、(1) 意味的重複排除でノイズを削減、(2) 嗜好ベクトルによる再ランクで好みの記事を Gemini 入力に残す。**ゼロコスト・障害無停止**の設計思想は維持（embedding 失敗時は現状動作にフォールバック）。

---

## 設計方針

| 論点 | 採用 | 理由 |
|---|---|---|
| embedding 提供元 | **Gemini embedding API**（`gemini-embedding-001`） | `google-genai` は既存依存（`gemini_selector.py:7`）。新規重量級依存（sentence-transformers 等）はゼロインフラ思想に反する。日次 ~200 記事 + ~100 履歴の埋め込みは無料枠内。 |
| 嗜好ベクトルの素材 | フィードバックの **title のみ** | `ArticleFeedback`（`models.py:29`）は title/source/url のみ保持。本文は無い。title 埋め込みで十分。 |
| 障害時の挙動 | **現状ロジックにフォールバック** | `GEMINI_API_KEY` 未設定・API 失敗時は URL dedup ＋ published_at 順に戻す。`return_exceptions` 哲学（`main.py:125`）を踏襲。 |
| 適用箇所 | dedup は `main.py` の URL dedup 直後、再ランクは `bucket_articles` の切り詰め前 | 既存パイプライン順序（README 処理フロー）を崩さず差し込む。 |

---

## アーキテクチャ / データ構造

### 新規モジュール `src/services/selector/embeddings.py`

embedding の取得・類似度計算を集約（コントラクト層）。実装は再生成可能に保つ。

```python
async def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Gemini embedding をバッチ取得。API キー無し・失敗時は None（呼び出し側がフォールバック）。"""

def cosine_sim(a: list[float], b: list[float]) -> float: ...

def semantic_dedup(
    articles: list[Article],
    embeddings: list[list[float]],
    threshold: float,
) -> list[Article]:
    """コサイン類似度 >= threshold の記事群をクラスタ化し、各クラスタから1件だけ残す。
    残す優先度: is_important > published_at が新しい > 元の順序（先着）。"""

def preference_centroids(
    feedback_embeddings: list[tuple[Literal["good","bad"], list[float]]],
) -> tuple[list[float] | None, list[float] | None]:
    """good 重心・bad 重心を返す（各々ベクトル平均、無ければ None）。"""

def preference_score(
    article_emb: list[float],
    good_centroid: list[float] | None,
    bad_centroid: list[float] | None,
) -> float:
    """sim(article, good) - sim(article, bad)。重心が無い側は 0 として扱う。"""
```

### config 追加（`src/core/config.py`）

```python
GEMINI_EMBED_MODEL = "gemini-embedding-001"
SEMANTIC_DEDUP_THRESHOLD = 0.88   # これ以上の類似度で同一トピックとみなす（要調整・config 可変）
ENABLE_SEMANTIC_DEDUP = True
ENABLE_PREFERENCE_RERANK = True
MAX_EMBED_TEXTS_PER_RUN = 400     # 1実行あたりの埋め込み上限ガード（記事＋履歴）。超過分は埋め込まずフォールバック
```

`embed_texts` は `MAX_EMBED_TEXTS_PER_RUN` を超える入力を受けたら超過分を埋め込まず、該当記事は dedup/再ランク対象外（＝現状動作）として扱う。ゼロコスト維持のためのセーフガード。

### モデル変更

`Article` / `SelectedArticle` への永続フィールド追加は **不要**（embedding はランタイム内のみで保持し KV に書かない）。KV スキーマ・ダッシュボード型は無変更 → 後方互換完全維持。

---

## 実装ステップ

### Step 1: `src/services/selector/embeddings.py` — embedding 基盤
- [x] `embed_texts`（バッチ取得、失敗時 None、上限ガード）
- [x] `cosine_sim` / `semantic_dedup` / `preference_centroids` / `preference_score`
- [x] テスト: `tests/test_embeddings.py`

### Step 2: 意味的重複排除をパイプラインに統合（`src/cli/main.py:138` 付近）
- [ ] URL dedup 直後に意味的 dedup を挿入
- [ ] フォールバック（embedding 失敗時は URL dedup 結果をそのまま使用）

### Step 3: 嗜好ベクトルによる再ランク（`src/services/selector/categorizer.py`）
- [ ] `bucket_articles` の切り詰め前に preference_score で再ランク
- [ ] embedding 不可・履歴空なら published_at 順フォールバック

### Step 4: config / README 反映
- [ ] 新 config 定数追加
- [ ] README の処理フロー・Gemini 選定節を更新

---

## 不明点・確認事項

[Q1] embedding コール回数の上限ガード（1日あたり）を設けるか？
[A1] Yes。`MAX_EMBED_TEXTS_PER_RUN`（初期値 400）で上限を設け、超過分はフォールバック。

[Q2] 意味的 dedup の閾値 `0.88` は初期値。config で可変にしておく。
[A2] Yes。config 定数で可変。

[Q3] 再ランクは切り詰めの順序のみ変える（件数は `gemini_max_input_per_category` のまま）。
[A3] Yes。件数は不変、順序のみ変更。
