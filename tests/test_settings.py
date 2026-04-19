from datetime import UTC, datetime

from src.core.models import Article, CategoryDef, UserSettings
from src.services.selector.categorizer import bucket_articles

_DEFAULT_CATS = [
    CategoryDef(
        id="backend", name="バックエンド",
        keywords=["java", "spring", "springboot", "spring boot", "postgres", "postgresql"],
        enabled=True, order=0,
    ),
    CategoryDef(
        id="frontend", name="フロントエンド",
        keywords=["react", "next.js", "nextjs", "typescript"],
        enabled=True, order=1,
    ),
    CategoryDef(
        id="aws", name="AWS",
        keywords=["aws", "amazon web services"],
        enabled=True, order=2,
    ),
    CategoryDef(
        id="management", name="マネジメント/組織",
        keywords=["engineering manager", "エンジニアリングマネージャー", "マネジメント"],
        enabled=True, order=3,
    ),
    CategoryDef(id="others", name="その他", keywords=[], enabled=True, order=4),
]
_MAX_INPUT = 25


def _make_article(
    url: str = "https://example.com/1",
    title: str = "Test",
    summary: str = "",
    source: str = "Zenn",
) -> Article:
    return Article(  # type: ignore[arg-type]
        title=title, url=url, summary=summary, source=source, published_at=datetime.now(UTC)
    )


class TestUserSettings:
    def test_default_values(self) -> None:
        s = UserSettings()
        assert s.categories == {}  # 空 dict は「全部 ON」扱い
        assert s.sources_enabled == {}
        assert s.max_per_category == 5
        assert s.exclude_keywords == []
        assert s.include_keywords == []

    def test_partial_override(self) -> None:
        s = UserSettings(max_per_category=3)
        assert s.max_per_category == 3
        assert s.categories.get("backend", True) is True

    def test_parse_from_dict(self) -> None:
        data = {"categories": {"backend": False}, "max_per_category": 2}
        s = UserSettings.model_validate(data)
        assert s.categories["backend"] is False
        assert s.max_per_category == 2


class TestArticleFiltering:
    def _make_backend_article(
        self, url: str = "https://example.com/b", source: str = "Zenn"
    ) -> Article:
        return _make_article(url=url, title="Spring Boot の最新機能", source=source)

    def test_category_off_empties_bucket(self) -> None:
        arts = [self._make_backend_article()]
        buckets = bucket_articles(arts, _DEFAULT_CATS, _MAX_INPUT)
        settings = UserSettings(categories={"backend": False})

        for cat_id in list(buckets.keys()):
            if not settings.categories.get(cat_id, True):
                buckets[cat_id] = []

        assert buckets["backend"] == []

    def test_source_disabled_filters_article(self) -> None:
        arts = [
            self._make_backend_article(url="https://example.com/1", source="Zenn"),
            self._make_backend_article(url="https://example.com/2", source="GitHub Blog"),
        ]
        buckets = bucket_articles(arts, _DEFAULT_CATS, _MAX_INPUT)
        settings = UserSettings(sources_enabled={"Zenn": False})

        for cat_id in list(buckets.keys()):
            buckets[cat_id] = [
                a for a in buckets[cat_id] if settings.sources_enabled.get(a.source, True)
            ]

        all_articles = [a for arts_list in buckets.values() for a in arts_list]
        sources = {a.source for a in all_articles}
        assert "Zenn" not in sources

    def test_exclude_keyword_removes_matching_article(self) -> None:
        arts = [
            _make_article(url="https://example.com/1", title="Rust の入門チュートリアル"),
            _make_article(url="https://example.com/2", title="Spring Boot 3.4 リリース"),
        ]
        buckets = bucket_articles(arts, _DEFAULT_CATS, _MAX_INPUT)
        lower_excludes = ["入門"]

        for cat_id in list(buckets.keys()):
            buckets[cat_id] = [
                a for a in buckets[cat_id]
                if not any(
                    kw in a.title.lower() or kw in a.summary.lower()
                    for kw in lower_excludes
                )
            ]

        all_titles = [a.title for arts_list in buckets.values() for a in arts_list]
        assert not any("入門" in t for t in all_titles)

    def test_empty_sources_enabled_keeps_all(self) -> None:
        arts = [
            self._make_backend_article(url="https://example.com/1", source="Zenn"),
            self._make_backend_article(url="https://example.com/2", source="GitHub Blog"),
        ]
        buckets = bucket_articles(arts, _DEFAULT_CATS, _MAX_INPUT)
        settings = UserSettings()  # sources_enabled = {}

        for cat_id in list(buckets.keys()):
            if settings.sources_enabled:
                buckets[cat_id] = [
                    a for a in buckets[cat_id]
                    if settings.sources_enabled.get(a.source, True)
                ]

        total = sum(len(v) for v in buckets.values())
        assert total == 2
