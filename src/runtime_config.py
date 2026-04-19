from pydantic import BaseModel

from src import config
from src.models import CategoryDef, SourceDef, UserSettings


class RuntimeConfig(BaseModel):
    sources: list[SourceDef]
    category_defs: list[CategoryDef]
    max_per_category: int
    article_fetch_hours: int
    gemini_max_input_per_category: int
    exclude_keywords: list[str]
    include_keywords: list[str]


def _merge_with_defaults(sources: list[SourceDef]) -> list[SourceDef]:
    """KV に登録されていないデフォルトソースを enabled=True で補完する。
    settings.sources が部分的に保存された場合でも全ソースを取得できるようにする。
    """
    existing_names = {s.name for s in sources}
    defaults = [SourceDef.model_validate(s) for s in config.default_sources()]
    extras = [s for s in defaults if s.name not in existing_names]
    return sources + extras


def _apply_sources_enabled(
    sources: list[SourceDef], sources_enabled: dict[str, bool]
) -> list[SourceDef]:
    if not sources_enabled:
        return sources
    return [
        s.model_copy(update={"enabled": sources_enabled[s.name]})
        if s.name in sources_enabled
        else s
        for s in sources
    ]


def _apply_categories_flag(
    cats: list[CategoryDef], categories: dict[str, bool]
) -> list[CategoryDef]:
    if not categories:
        return cats
    return [
        c.model_copy(update={"enabled": categories[c.id]})
        if c.id in categories
        else c
        for c in cats
    ]


def build_runtime_config(settings: UserSettings) -> RuntimeConfig:
    # --- sources ---
    if settings.sources is not None:
        raw_sources = _merge_with_defaults(list(settings.sources))
    else:
        raw_sources = [SourceDef.model_validate(s) for s in config.default_sources()]

    raw_sources = _apply_sources_enabled(raw_sources, settings.sources_enabled)
    enabled_sources = [s for s in raw_sources if s.enabled]

    # --- category_defs ---
    if settings.category_defs is not None:
        raw_cats = list(settings.category_defs)
    else:
        raw_cats = [CategoryDef.model_validate(c) for c in config.default_category_defs()]

    raw_cats = _apply_categories_flag(raw_cats, settings.categories)
    enabled_cats = sorted([c for c in raw_cats if c.enabled], key=lambda c: c.order)

    return RuntimeConfig(
        sources=enabled_sources,
        category_defs=enabled_cats,
        max_per_category=settings.max_per_category,
        article_fetch_hours=(
            settings.article_fetch_hours
            if settings.article_fetch_hours is not None
            else config.ARTICLE_FETCH_HOURS
        ),
        gemini_max_input_per_category=(
            settings.gemini_max_input_per_category
            if settings.gemini_max_input_per_category is not None
            else config.GEMINI_MAX_INPUT_PER_CATEGORY
        ),
        exclude_keywords=settings.exclude_keywords,
        include_keywords=settings.include_keywords,
    )
