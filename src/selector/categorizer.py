from datetime import UTC, datetime

from src.models import Article, CategoryDef

_EPOCH = datetime.min.replace(tzinfo=UTC)


def classify(article: Article, category_defs: list[CategoryDef]) -> str:
    """タイトル + サマリのキーワードマッチで大カテゴリ ID を返す。
    先にリストされたカテゴリが優先。どれにもマッチしなければ "others"。
    """
    text = (article.title + " " + (article.summary or "")).lower()
    for cat in category_defs:
        if cat.id == "others":
            continue
        if any(kw in text for kw in cat.keywords):
            return cat.id
    return "others"


def bucket_articles(
    articles: list[Article],
    category_defs: list[CategoryDef],
    gemini_max_input: int,
) -> dict[str, list[Article]]:
    """記事リストを大カテゴリごとにバケット分けして返す。
    各バケットは published_at 降順でソートされ gemini_max_input 件に切り詰められる。
    """
    buckets: dict[str, list[Article]] = {cat.id: [] for cat in category_defs}
    for article in articles:
        cat_id = classify(article, category_defs)
        if cat_id in buckets:
            buckets[cat_id].append(article)
    for cat_id in buckets:
        buckets[cat_id].sort(
            key=lambda a: a.published_at if a.published_at else _EPOCH,
            reverse=True,
        )
        buckets[cat_id] = buckets[cat_id][:gemini_max_input]
    return buckets
