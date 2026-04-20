from src.core import config
from src.core.models import CategoryDef, SourceDef, UserSettings
from src.core.runtime_config import RuntimeConfig, build_runtime_config


def _default_src_count() -> int:
    return len([s for s in config.default_sources() if s.get("enabled", True)])


def _default_cat_count() -> int:
    return len([c for c in config.default_category_defs() if c.get("enabled", True)])


# (a) v2 sources → merged with defaults; disabled entries remain excluded
def test_v2_sources_filters_disabled() -> None:
    settings = UserSettings(
        sources=[
            SourceDef(name="SourceA", type="rss", url="https://a.com/feed", enabled=True),
            SourceDef(name="SourceB", type="rss", url="https://b.com/feed", enabled=False),
        ],
        category_defs=[
            CategoryDef(
                id="backend", name="バックエンド", keywords=["java"], enabled=True, order=0
            ),
            CategoryDef(
                id="frontend", name="フロントエンド", keywords=["react"], enabled=False, order=1
            ),
        ],
    )
    rc = build_runtime_config(settings)
    # SourceA (enabled) + all defaults (enabled); SourceB (disabled) is excluded
    source_names = [s.name for s in rc.sources]
    assert "SourceA" in source_names
    assert "SourceB" not in source_names
    assert len(rc.sources) == 1 + _default_src_count()
    assert len(rc.category_defs) == 1
    assert rc.category_defs[0].id == "backend"


# (b) empty UserSettings → all config defaults
def test_empty_settings_uses_all_defaults() -> None:
    settings = UserSettings()
    rc = build_runtime_config(settings)
    assert len(rc.sources) == _default_src_count()
    assert len(rc.category_defs) == _default_cat_count()
    assert rc.article_fetch_hours == config.ARTICLE_FETCH_HOURS
    assert rc.gemini_max_input_per_category == config.GEMINI_MAX_INPUT_PER_CATEGORY
    assert rc.max_per_category == 5


# article_fetch_hours / gemini_max_input_per_category
def test_article_fetch_hours_from_settings() -> None:
    settings = UserSettings(article_fetch_hours=48)
    rc = build_runtime_config(settings)
    assert rc.article_fetch_hours == 48


def test_gemini_max_input_from_settings() -> None:
    settings = UserSettings(gemini_max_input_per_category=10)
    rc = build_runtime_config(settings)
    assert rc.gemini_max_input_per_category == 10


# category_defs sorted by order
def test_category_defs_sorted_by_order() -> None:
    settings = UserSettings(
        category_defs=[
            CategoryDef(id="frontend", name="F", keywords=[], enabled=True, order=2),
            CategoryDef(id="backend", name="B", keywords=[], enabled=True, order=0),
            CategoryDef(id="aws", name="A", keywords=[], enabled=True, order=1),
        ],
    )
    rc = build_runtime_config(settings)
    assert [c.id for c in rc.category_defs] == ["backend", "aws", "frontend"]


# exclude_keywords / include_keywords pass through
def test_keywords_pass_through() -> None:
    settings = UserSettings(exclude_keywords=["spam"], include_keywords=["java"])
    rc = build_runtime_config(settings)
    assert rc.exclude_keywords == ["spam"]
    assert rc.include_keywords == ["java"]


# RuntimeConfig is a Pydantic model
def test_runtime_config_is_valid_model() -> None:
    settings = UserSettings()
    rc = build_runtime_config(settings)
    assert isinstance(rc, RuntimeConfig)
