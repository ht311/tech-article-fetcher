from collections import Counter
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class Article(BaseModel):
    """フェッチした生の記事。全ソース共通のデータ構造。"""

    title: str
    url: HttpUrl
    summary: str = ""
    source: str  # フィード名（例: "Zenn", "GitHub Blog"）
    published_at: datetime | None = None  # 取得できない場合は None
    thumbnail_url: str | None = None  # OGP等のサムネイル画像URL
    is_important: bool = False  # 重要ソース由来（ピン留め＆延長ウィンドウ対象）


class SelectedArticle(BaseModel):
    """Gemini が選定した記事と、その選定理由のペア。"""

    article: Article
    reason: str  # 日本語30字以内の選定理由
    summary: str = ""  # Gemini 生成の短い要約（日本語・最大100字）
    category_id: str | None = None


class ArticleFeedback(BaseModel):
    """ユーザーが LINE Quick Reply で評価した記事のフィードバック。"""

    action: Literal["good", "bad"]
    title: str
    source: str
    url: str
    timestamp: datetime


class SourceDef(BaseModel):
    """RSS / Qiita / SpeakerDeck / Docswell ソースの定義。"""

    name: str
    type: Literal["rss", "qiita", "speakerdeck", "docswell"]
    url: str | None = None
    params: dict[str, Any] | None = None
    enabled: bool = True
    important: bool = False  # True なら延長ウィンドウで取得・ピン留め対象


class CategoryDef(BaseModel):
    """大カテゴリの定義。"""

    id: str
    name: str
    keywords: list[str] = []
    enabled: bool = True
    order: int = 0


class UserSettings(BaseModel):
    """配信設定。Cloudflare KV の `settings` キーに永続化される。"""

    max_per_category: int = 5
    exclude_keywords: list[str] = []
    include_keywords: list[str] = []
    sources: list[SourceDef] | None = None
    category_defs: list[CategoryDef] | None = None
    article_fetch_hours: int | None = None
    gemini_max_input_per_category: int | None = None
    semantic_dedup_threshold: float | None = Field(default=None, ge=0.5, le=1.0)


class Conference(BaseModel):
    """カンファレンス名とメタデータ。KV `conferences` に永続化。"""

    name: str
    added_at: datetime
    last_seen_at: datetime | None = None


class ConferenceList(BaseModel):
    """週次ジョブが育てるカンファレンス名リスト。"""

    conferences: list[Conference] = []


class UserPreferences(BaseModel):
    """ユーザーの評価履歴。Cloudflare KV に永続化される。"""

    history: list[ArticleFeedback] = []

    def get_summary(self, known_topics: list[str] | None = None) -> str:
        """Gemini プロンプト用の嗜好サマリーを生成する。履歴が空の場合は空文字を返す。

        known_topics を渡すと、評価済み記事タイトルとのキーワードマッチで
        高評価/低評価トピックを追加集計する。
        """
        if not self.history:
            return ""

        good = [f for f in self.history if f.action == "good"]
        bad = [f for f in self.history if f.action == "bad"]

        lines: list[str] = ["ユーザーの過去の評価傾向（参考情報）:"]

        if good:
            good_sources = Counter(f.source for f in good).most_common(3)
            src_str = ", ".join(f"{s} ({c}件)" for s, c in good_sources)
            lines.append(f"- 高評価したソース: {src_str}")

        if bad:
            bad_sources = Counter(f.source for f in bad).most_common(3)
            src_str = ", ".join(f"{s} ({c}件)" for s, c in bad_sources)
            lines.append(f"- 低評価したソース: {src_str}")

        if known_topics:
            vocab = [t.lower() for t in known_topics if t]

            good_topics: Counter[str] = Counter()
            for f in good:
                title_lower = f.title.lower()
                for kw in vocab:
                    if kw in title_lower:
                        good_topics[kw] += 1

            bad_topics: Counter[str] = Counter()
            for f in bad:
                title_lower = f.title.lower()
                for kw in vocab:
                    if kw in title_lower:
                        bad_topics[kw] += 1

            if good_topics:
                kw_str = ", ".join(kw for kw, _ in good_topics.most_common(3))
                lines.append(f"- 高評価したトピック: {kw_str}")
            if bad_topics:
                kw_str = ", ".join(kw for kw, _ in bad_topics.most_common(3))
                lines.append(f"- 低評価したトピック: {kw_str}")

        lines.append("\nこの傾向を参考にしつつ、多様性も維持してください。")
        return "\n".join(lines)
