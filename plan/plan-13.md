# Gemini 記事要約 + トピック嗜好学習の実装計画 (plan-13)

## Context

- **きっかけ**: リポジトリへの機能追加検討。ユーザーは「トピック嗜好学習」と「Gemini記事要約」の2機能を選択。
- **現状の課題**:
  1. LINE に表示される説明は Gemini の選定理由（`reason`, 30字以内）のみ。記事本文の要約はなく、RSS の生 `summary`（`Article.summary`）は表示にも履歴にも使われていない（`line_notifier.py:62-73`、`preferences.py:194-203`）。
  2. フィードバック学習はソース別集計のみ。`UserPreferences.get_summary()`（`models.py:90-111`）は `Counter(f.source)` だけで、トピック傾向を一切学習しない（README にも「トピック集計は行わない」と明記）。
- **ゴール**:
  1. Gemini が選定と同時に各記事の短い要約を生成し、LINE Flex Message・KV履歴・ダッシュボードに表示する。**追加 API コールなし**（既存の1カテゴリ1コールの出力を拡張するだけ）でコスト $0 を維持。
  2. 👍/👎 履歴のタイトルを既存トピック語彙とマッチさせ、高評価/低評価トピックを Gemini プロンプトに反映する。**Worker/KV/モデルのスキーマ変更なし**でマイグレーション不要。

---

## 設計方針

| 論点 | 採用案 | 理由 |
|---|---|---|
| 要約の生成方法 | 既存の per-category Gemini コールの出力 JSON を `{index, reason, summary}` に拡張 | 追加コールゼロでコスト維持。`_call_gemini` の retry/fallback 機構をそのまま再利用 |
| 要約の格納先 | `SelectedArticle.summary`（新フィールド）。`Article.summary`（生RSS）は据え置き | 選定済み記事だけに付与すればよく、notifier/storage 両方に流れる |
| トピック抽出 | `get_summary()` 内で評価記事タイトルを既存語彙（category_defs.keywords + PREFERRED_TOPICS + include_keywords）とマッチ | Python完結・Worker/KV変更なし・低リスク（ユーザー選択済み） |
| 要約が無い場合 | `_pin_important` のピン留め記事・Gemini失敗時のフォールバックは `Article.summary` を切り詰めて代用、無ければ空 | 既存挙動を壊さず graceful |

---

## アーキテクチャ / データ構造

**`SelectedArticle`（`src/core/models.py:20-25`）にフィールド追加**:
```python
class SelectedArticle(BaseModel):
    article: Article
    reason: str
    summary: str = ""          # ← 追加: Gemini生成の短い要約（日本語・3行/〜100字）
    category_id: str | None = None
```

**Gemini 出力フォーマット変更**（プロンプト指示）:
```
[{"index": 0, "reason": "選定理由（30字以内）", "summary": "要約（80〜100字・最大3行）"}, ...]
```

トピック語彙は `get_summary()` に渡す（モデルを config に密結合させない）:
```python
def get_summary(self, known_topics: list[str] | None = None) -> str: ...
```

---

## 実装ステップ

### Feature A: Gemini 記事要約

#### Step A1: `src/core/models.py` — SelectedArticle に `summary: str = ""` を追加
[ ] line 24 付近にフィールド追加

#### Step A2: `src/services/selector/gemini_selector.py` — 要約を生成・パース
[ ] `_build_system_prompt`（25-64）: 出力フォーマット指示（56-57行）を `{index, reason, summary}` に変更し、summary の文字数・行数ガイドを追記
[ ] `_call_gemini`（111-118）: `item.get("summary", "")` を読み、`SelectedArticle(..., summary=...)` に設定
[ ] `_fallback_selection`（142-146）: summary は `articles[0].summary[:100]` を代用

#### Step A3: `src/services/notifier/line_notifier.py` — 要約を表示
[ ] `_build_article_box`（62-73）: タイトル（62-67）と reason（68-73）の間に summary の `FlexText`（size="xs", wrap=True）を追加。`s.summary` が空なら描画スキップ

#### Step A4: `src/services/storage/preferences.py` — 履歴に要約を保存
[ ] `write_article_history` の flat dict（194-203）に `"summary": s.summary` を追加

#### Step A5: `src/cli/main.py` — ピン留め記事の要約代用
[ ] `_pin_important`（57-80）: 生成する `SelectedArticle` に `summary=a.summary[:100]` を設定

### Feature B: トピック嗜好学習

#### Step B1: `src/core/models.py` — `get_summary()` をトピック対応に拡張
[ ] シグネチャを `get_summary(self, known_topics: list[str] | None = None)` に変更
[ ] 既存のソース集計（95-108）の後に、`known_topics` があれば good/bad のタイトル（小文字化）に含まれる語を `Counter` で集計し「高評価トピック / 低評価トピック」上位3件を追記
[ ] `known_topics` が None/空なら従来通りソースのみ（後方互換）

#### Step B2: `src/services/selector/gemini_selector.py` — 語彙を構築して渡す
[ ] `select_articles_by_category`（197付近）: category_defs.keywords + `config.PREFERRED_TOPICS` + `settings.include_keywords` を重複排除して `known_topics` を構築し `preferences.get_summary(known_topics)` で呼ぶ
[ ] 語彙構築は小さなヘルパー関数に切り出す

---

## テスト方針

- `tests/test_selector.py`:
  - 既存の `test_select_articles_by_category_success`（153-172）のモック応答に `summary` を含め、`SelectedArticle.summary` がセットされることを assert
  - Gemini が `summary` を返さない場合に空文字で graceful に動くこと
- `tests/test_models.py`（無ければ新規）:
  - `get_summary()` のトピック集計: good/bad タイトルに語彙語を含むケースで「高評価/低評価トピック」行が出ること、`known_topics=None` で従来出力になること
- `tests/test_notifier.py`:
  - `_build_article_box` / Flex 構築で summary がある場合とない場合の描画分岐
- `tests/test_plan12.py` の `write_article_history` 系があれば flat dict に `summary` キーが入ることを確認

全体: `pytest tests/ -v` / `ruff check src/ tests/` / `mypy src/` を通す。`python -m src` での動作確認（.env 設定時）。

---

## 不明点・確認事項

[Q1] 要約の長さは「最大3行・80〜100字」を想定。LINE Flex の視認性的にこの範囲でよいか？（短め推奨）
[A1]

[Q2] ダッシュボード（`dashboard/`）側に要約表示を追加するところまで今回スコープに含めるか？（KV履歴には保存するので、表示追加は別PRでも可）
[A2]

[Q3] トピック語彙に `PREFERRED_TOPICS` を含めると範囲が広め。category_defs.keywords + include_keywords のみに絞る案もあるが、広めで開始してよいか？
[A3]

---

## メモ
- 確定後の実際の計画ファイルは `plan/plan-13.md` に作成する（既存最大が plan-12）。
- 両機能とも追加 Gemini コールなし・KV/Worker スキーマ変更なしで、README の「$0/月」「マイグレーション不要」方針を維持。
