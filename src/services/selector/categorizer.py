import re
from datetime import UTC, datetime
from functools import lru_cache

from src.core.models import Article, CategoryDef

_EPOCH = datetime.min.replace(tzinfo=UTC)


@lru_cache(maxsize=1024)
def _ascii_pattern(kw: str) -> re.Pattern[str]:
    # \b は日本語文字も \w 扱いのため「lambdaで作る」にマッチしなくなる。
    # 前後が ASCII 英数字でないことだけを境界条件にする。
    return re.compile(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])")


def _kw_match(kw: str, text: str) -> bool:
    """ASCII キーワードは英数字境界付きでマッチさせる（"specs" の "ecs" 等の誤爆防止）。
    日本語を含むキーワードは従来通り部分一致。text は小文字化済み前提。
    """
    kw = kw.lower()
    if kw.isascii():
        return _ascii_pattern(kw).search(text) is not None
    return kw in text


def classify(article: Article, category_defs: list[CategoryDef]) -> str:
    """タイトル + サマリのキーワードマッチで大カテゴリ ID を返す。
    先にリストされたカテゴリが優先。どれにもマッチしなければ "others"。
    """
    text = (article.title + " " + (article.summary or "")).lower()
    for cat in category_defs:
        if cat.id == "others":
            continue
        if any(_kw_match(kw, text) for kw in cat.keywords):
            return cat.id
    return "others"


def bucket_articles(
    articles: list[Article],
    category_defs: list[CategoryDef],
    gemini_max_input: int,
    url_to_score: dict[str, float] | None = None,
) -> dict[str, list[Article]]:
    """記事リストを大カテゴリごとにバケット分けして返す。

    各バケットは gemini_max_input 件に切り詰められる。ソート順:
    - url_to_score が渡された場合: 嗜好スコア降順 → published_at 降順（好みの記事を優先して残す）
    - 渡されない場合: published_at 降順（従来動作）
    """
    buckets: dict[str, list[Article]] = {cat.id: [] for cat in category_defs}
    for article in articles:
        cat_id = classify(article, category_defs)
        if cat_id in buckets:
            buckets[cat_id].append(article)

    for cat_id in buckets:
        if url_to_score is not None:
            buckets[cat_id].sort(
                key=lambda a: (
                    url_to_score.get(str(a.url), 0.0),
                    a.published_at if a.published_at else _EPOCH,
                ),
                reverse=True,
            )
        else:
            buckets[cat_id].sort(
                key=lambda a: a.published_at if a.published_at else _EPOCH,
                reverse=True,
            )
        buckets[cat_id] = buckets[cat_id][:gemini_max_input]
    return buckets
