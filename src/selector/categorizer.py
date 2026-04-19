from datetime import datetime, timezone

from src.config import CATEGORIES, GEMINI_MAX_INPUT_PER_CATEGORY
from src.models import Article

_EPOCH = datetime.min.replace(tzinfo=timezone.utc)


def classify(article: Article) -> str:
    """タイトル + サマリのキーワードマッチで大カテゴリ ID を返す。
    先にリストされたカテゴリが優先される。どれにもマッチしなければ "others"。
    """
    text = (article.title + " " + (article.summary or "")).lower()
    for cat in CATEGORIES:
        if cat["id"] == "others":
            continue
        if any(kw in text for kw in cat["keywords"]):
            return cat["id"]
    return "others"


def bucket_articles(articles: list[Article]) -> dict[str, list[Article]]:
    """記事リストを大カテゴリごとにバケット分けして返す。
    各バケットは published_at 降順でソートされ、GEMINI_MAX_INPUT_PER_CATEGORY 件に切り詰められる。
    """
    buckets: dict[str, list[Article]] = {cat["id"]: [] for cat in CATEGORIES}
    for article in articles:
        cat_id = classify(article)
        buckets[cat_id].append(article)
    for cat_id in buckets:
        buckets[cat_id].sort(
            key=lambda a: a.published_at if a.published_at else _EPOCH,
            reverse=True,
        )
        buckets[cat_id] = buckets[cat_id][:GEMINI_MAX_INPUT_PER_CATEGORY]
    return buckets
