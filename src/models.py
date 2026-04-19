from collections import Counter
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, HttpUrl


class Article(BaseModel):
    """フェッチした生の記事。全ソース共通のデータ構造。"""

    title: str
    url: HttpUrl
    summary: str = ""
    source: str  # フィード名（例: "Zenn", "GitHub Blog"）
    published_at: datetime | None = None  # 取得できない場合は None
    thumbnail_url: str | None = None  # OGP等のサムネイル画像URL


class SelectedArticle(BaseModel):
    """Gemini が選定した記事と、その選定理由のペア。"""

    article: Article
    reason: str  # 日本語30字以内の選定理由
    category_id: str | None = None


class ArticleFeedback(BaseModel):
    """ユーザーが LINE Quick Reply で評価した記事のフィードバック。"""

    action: Literal["good", "bad"]
    title: str
    source: str
    url: str
    timestamp: datetime


class SourceDef(BaseModel):
    """RSS / Qiita / SpeakerDeck ソースの定義。"""

    name: str
    type: Literal["rss", "qiita", "speakerdeck"]
    url: str | None = None
    params: dict[str, Any] | None = None
    enabled: bool = True


class CategoryDef(BaseModel):
    """大カテゴリの定義。"""

    id: str
    name: str
    keywords: list[str] = []
    enabled: bool = True
    order: int = 0


class UserSettings(BaseModel):
    """配信設定。Cloudflare KV の `settings` キーに永続化される。"""

    # v1 互換フィールド（空 dict は「全部 ON」扱い。sources_enabled と同じ規則）
    categories: dict[str, bool] = {}
    sources_enabled: dict[str, bool] = {}
    max_per_category: int = 5
    exclude_keywords: list[str] = []
    include_keywords: list[str] = []

    # v2 新フィールド（未設定時は fetcher が config デフォルトを使用）
    sources: list[SourceDef] | None = None
    category_defs: list[CategoryDef] | None = None
    article_fetch_hours: int | None = None
    gemini_max_input_per_category: int | None = None
    schema_version: Literal[1, 2] | None = None


class UserPreferences(BaseModel):
    """ユーザーの評価履歴。Cloudflare KV に永続化される。"""

    history: list[ArticleFeedback] = []

    def get_summary(self) -> str:
        """Gemini プロンプト用の嗜好サマリーを生成する。履歴が空の場合は空文字を返す。"""
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

        lines.append("\nこの傾向を参考にしつつ、多様性も維持してください。")
        return "\n".join(lines)
