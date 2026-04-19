# Gemini APIレート制限対策計画

## 問題の再分析

### 観察された事実
- 1日1回（JST 8:00）のみワークフロー実行
- 起動直後（記事フェッチ完了後の最初のGemini呼び出し）で即429
- `gemini-2.0-flash` と `gemini-2.0-flash-lite` 両方が同時に失敗
- エラー内容: `limit: 0`

### `limit: 0` の意味

```
Quota exceeded for metric: generate_content_free_tier_requests, limit: 0
```

これは「今日の残りが0件になった」ではなく、
**「この指標に割り当てられたクォータ上限が 0 に設定されている」** を示している。

通常の無料枠上限は `gemini-2.0-flash` で 1,500 req/day。
1日1回しか呼ばないのに枯渇するはずがない → **クォータ設定が壊れているか、無効化されている**。

---

## 根本原因の候補

### 候補1: Google Cloud プロジェクトで無料枠が無効化されている

Google AI Studio 経由で取得したAPIキーと、
Google Cloud Console で作成したAPIキーではクォータプールが異なる場合がある。
プロジェクトの状態によっては無料枠クォータが 0 に設定される。

**確認方法**:
1. [Google Cloud Console](https://console.cloud.google.com/) → 該当プロジェクト → 「APIとサービス」→「クォータ」
2. `Generative Language API` で検索
3. `generate_content_free_tier_requests` の `Per day` クォータ値を確認
4. 0 や無効になっていれば、ここが原因

### 候補2: 請求先アカウントの状態

- 一部の Google Cloud プロジェクト構成では、無料枠でも請求先アカウントのリンクが必要
- 請求先がリンクされていないプロジェクトでクォータが 0 になることがある

**確認方法**:
Google Cloud Console → 「お支払い」→ 請求先アカウントがプロジェクトにリンクされているか確認

### 候補3: APIキーが Google AI Studio のものではなく Google Cloud のもの

- Google AI Studio (aistudio.google.com) で取得したキー → 無料枠あり
- Google Cloud Console の Credentials で作成したキー → 無料枠の扱いが異なる

**確認方法**:
`GEMINI_API_KEY` の先頭が `AIza` で始まるか確認。
どちらも `AIza` 始まりなので、どのプロジェクトで発行したかを確認する必要がある。

---

## 調査手順（優先順）

```
Step 1. Google Cloud Console でクォータ値を直接確認
  → "Generative Language API" > "generate_content_free_tier_requests"
  → limit が 0 なら候補1が原因

Step 2. APIキーの発行元を確認
  → Google AI Studio で発行したキーか？
  → Google Cloud Console で発行したキーか？

Step 3. 別のAPIキーで試す
  → Google AI Studio (aistudio.google.com) でキーを新規発行
  → 既存キーと差し替えてローカルで python -m src.main を実行
```

---

## 原因確認後の対応策

### ケースA: クォータが 0 に設定されている場合
Google Cloud Console からクォータの上限を手動で引き上げるか、
Google AI Studio で新しいキーを発行して差し替える。

### ケースB: Google AI Studio 以外のキーを使っている場合
aistudio.google.com でキーを再発行し、GitHub Secrets の `GEMINI_API_KEY` を更新する。

---

## 暫定対策（根本原因調査中の保険）

原因調査中もフォールバック品質を上げておく価値はある。

### モデルリストの拡張（`src/config.py`）

```python
# gemini-1.5-flash は独立したクォータプールを持つ可能性がある
GEMINI_MODELS: list[str] = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
]
```

`src/selector/gemini_selector.py` の `select_articles()` をリスト順に試行するよう変更。

### ルールベースフォールバックの改善（`src/selector/gemini_selector.py`）

現状の「最新記事+ソース分散」より高品質な選定にする。

```python
def _fallback_select(articles: list[Article]) -> list[SelectedArticle]:
    import math
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    epoch = datetime.min.replace(tzinfo=timezone.utc)

    SOURCE_WEIGHTS: dict[str, float] = {
        "GitHub Blog": 1.3, "Cloudflare Blog": 1.2, "Zenn": 1.2,
        "AWS Blog": 1.1, "はてブIT": 1.0, "Qiita人気記事": 1.0,
    }
    topic_keywords = [t.lower() for t in PREFERRED_TOPICS]

    def score(a: Article) -> float:
        age_hours = (now - a.published_at).total_seconds() / 3600 if a.published_at else 48
        recency = math.exp(-age_hours / 24)                          # 0〜1
        text = (a.title + " " + (a.summary or "")).lower()
        topic_score = min(sum(1 for kw in topic_keywords if kw in text) * 0.3, 1.0)
        source_bonus = SOURCE_WEIGHTS.get(a.source, 1.0) - 1.0      # 0〜0.3
        return recency * 0.4 + topic_score * 0.4 + source_bonus * 0.2

    scored = sorted(articles, key=score, reverse=True)
    seen_sources: set[str] = set()
    selected: list[SelectedArticle] = []
    for article in scored:
        if article.source not in seen_sources or len(selected) < SELECT_MIN:
            seen_sources.add(article.source)
            selected.append(SelectedArticle(article=article, reason="スコアリング選定"))
        if len(selected) >= SELECT_MAX:
            break

    logger.info("Rule-based fallback selected %d articles", len(selected))
    return selected
```

---

## スコープ外（採用しない案）

- **実行時刻の変更**: 配信時刻 JST 8:00 は維持。そもそも日次クォータ枯渇ではないため無意味
- **Groq API追加**: 新規APIキー管理コストに見合わない
- **スリープ+リトライ（日次クォータエラーに対して）**: `retryDelay: 43s` は分単位クォータ用。日次クォータには無意味
- **Gemini完全廃止**: 根本原因を解決すれば不要
