from datetime import datetime

from pydantic import BaseModel, HttpUrl


class Article(BaseModel):
    """フェッチした生の記事。全ソース共通のデータ構造。"""

    title: str
    url: HttpUrl
    summary: str = ""
    source: str  # フィード名（例: "Zenn", "GitHub Blog"）
    published_at: datetime | None = None  # 取得できない場合は None


class SelectedArticle(BaseModel):
    """Gemini が選定した記事と、その選定理由のペア。"""

    article: Article
    reason: str  # 日本語30字以内の選定理由
