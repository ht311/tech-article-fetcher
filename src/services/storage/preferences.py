"""Cloudflare KV を介してユーザー嗜好データを読み書きするモジュール。

環境変数:
  CLOUDFLARE_API_TOKEN       - Cloudflare API トークン
  CLOUDFLARE_ACCOUNT_ID      - Cloudflare アカウント ID
  CLOUDFLARE_KV_NAMESPACE_ID - KV Namespace ID

上記が未設定の場合は graceful degradation（空の嗜好を返す・書き込みをスキップ）。
"""

import json
import logging
import os
from datetime import UTC, datetime, timedelta

import httpx

from src.core.constants import ARTICLE_RETENTION_DAYS, MAX_HISTORY
from src.core.kv_keys import (
    KV_ARTICLE_HISTORY_PREFIX,
    KV_ARTICLE_INDEX,
    KV_DEFAULT_SETTINGS,
    KV_LAST_ARTICLES,
    KV_PREFERENCES,
    KV_SETTINGS,
)
from src.core.models import (
    ArticleFeedback,
    CategoryDef,
    SelectedArticle,
    UserPreferences,
    UserSettings,
)

logger = logging.getLogger(__name__)


def _kv_base_url() -> str | None:
    """KV REST API のベース URL を返す。環境変数未設定時は None。"""
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    namespace_id = os.getenv("CLOUDFLARE_KV_NAMESPACE_ID")
    if not account_id or not namespace_id:
        return None
    return (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/storage/kv/namespaces/{namespace_id}/values"
    )


def _auth_headers() -> dict[str, str]:
    token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    return {"Authorization": f"Bearer {token}"}


async def get_preferences() -> UserPreferences:
    """Cloudflare KV から嗜好データを取得する。
    KV未設定・取得失敗時は空の UserPreferences を返す。
    """
    base_url = _kv_base_url()
    if not base_url:
        logger.debug("Cloudflare KV not configured. Using empty preferences.")
        return UserPreferences()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/{KV_PREFERENCES}",
                headers=_auth_headers(),
                timeout=10,
            )
        if response.status_code == 404:
            return UserPreferences()
        response.raise_for_status()
        data = response.json()
        return UserPreferences.model_validate(data)
    except Exception as exc:
        logger.warning("Failed to read preferences from KV: %s", exc)
        return UserPreferences()


async def write_last_articles(
    articles: list[SelectedArticle] | dict[str, list[SelectedArticle]],
    category_defs: list[CategoryDef] | None = None,
) -> None:
    """送信した記事リストを KV に保存する。
    Cloudflare Worker が「👍N」フィードバック受信時に記事情報を照合するために使う。
    dict[category_id, list] を渡した場合は category_defs 順にフラット化する。
    """
    base_url = _kv_base_url()
    if not base_url:
        logger.debug("Cloudflare KV not configured. Skipping last_articles write.")
        return

    flat: list[SelectedArticle]
    if isinstance(articles, dict):
        flat = []
        if category_defs is not None:
            for cat in category_defs:
                flat.extend(articles.get(cat.id, []))
        else:
            for items in articles.values():
                flat.extend(items)
    else:
        flat = articles

    data = {
        str(i + 1): {
            "title": sa.article.title,
            "source": sa.article.source,
            "url": str(sa.article.url),
        }
        for i, sa in enumerate(flat)
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{base_url}/{KV_LAST_ARTICLES}",
                headers={**_auth_headers(), "Content-Type": "application/json"},
                content=json.dumps(data),
                timeout=10,
            )
        response.raise_for_status()
        logger.info("Wrote last_articles to KV (%d articles)", len(flat))
    except Exception as exc:
        logger.warning("Failed to write last_articles to KV: %s", exc)


async def get_settings() -> UserSettings:
    """Cloudflare KV から配信設定を取得する。未設定・失敗時はデフォルト設定を返す。"""
    base_url = _kv_base_url()
    if not base_url:
        return UserSettings()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/{KV_SETTINGS}",
                headers=_auth_headers(),
                timeout=10,
            )
        if response.status_code == 404:
            return UserSettings()
        response.raise_for_status()
        return UserSettings.model_validate(response.json())
    except Exception as exc:
        logger.warning("Failed to read settings from KV: %s", exc)
        return UserSettings()


async def write_default_settings(settings: UserSettings) -> None:
    """src/core/config.py のデフォルト設定を KV の default_settings キーに保存する。
    dashboard の「ソースを初期化する」ボタンがこのキーを参照する。
    """
    base_url = _kv_base_url()
    if not base_url:
        logger.debug("Cloudflare KV not configured. Skipping default_settings write.")
        return
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{base_url}/{KV_DEFAULT_SETTINGS}",
                headers={**_auth_headers(), "Content-Type": "application/json"},
                content=settings.model_dump_json(),
                timeout=10,
            )
        response.raise_for_status()
        logger.info("Wrote default_settings to KV")
    except Exception as exc:
        logger.warning("Failed to write default_settings to KV: %s", exc)


async def write_article_history(
    date: str,
    selections: dict[str, list[SelectedArticle]],
    category_defs: list[CategoryDef] | None = None,
) -> None:
    """配信した記事を日付キーで KV に保存し、article_index を更新する。
    90日より古い日付エントリは index から削除し、対応する KV キーも消す。
    """
    base_url = _kv_base_url()
    if not base_url:
        logger.debug("Cloudflare KV not configured. Skipping article_history write.")
        return

    # 日別記事データを構築 (category_defs 順、未指定なら dict 順)
    flat: list[dict[str, object]] = []
    cat_ids = [c.id for c in category_defs] if category_defs else list(selections.keys())
    for cat_id in cat_ids:
        for sa in selections.get(cat_id, []):
            flat.append({
                "title": sa.article.title,
                "source": sa.article.source,
                "url": str(sa.article.url),
                "category_id": sa.category_id,
                "reason": sa.reason,
                "thumbnail_url": sa.article.thumbnail_url,
                "published_at": (
                    sa.article.published_at.isoformat() if sa.article.published_at else None
                ),
            })

    async with httpx.AsyncClient() as client:
        # 日別記事を保存
        try:
            r = await client.put(
                f"{base_url}/{KV_ARTICLE_HISTORY_PREFIX}{date}",
                headers={**_auth_headers(), "Content-Type": "application/json"},
                content=json.dumps(flat),
                timeout=10,
            )
            r.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to write article history for %s: %s", date, exc)
            return

        # article_index を更新
        try:
            idx_resp = await client.get(
                f"{base_url}/{KV_ARTICLE_INDEX}",
                headers=_auth_headers(),
                timeout=10,
            )
            if idx_resp.status_code == 404:
                index: dict[str, list[str]] = {"dates": []}
            else:
                idx_resp.raise_for_status()
                index = idx_resp.json()
        except Exception as exc:
            logger.warning("Failed to read article_index: %s", exc)
            index = {"dates": []}

        dates: list[str] = index.get("dates", [])
        if date not in dates:
            dates.append(date)

        cutoff = (
            datetime.now(UTC) - timedelta(days=ARTICLE_RETENTION_DAYS)
        ).strftime("%Y-%m-%d")
        expired = [d for d in dates if d < cutoff]
        dates = [d for d in dates if d >= cutoff]

        try:
            r = await client.put(
                f"{base_url}/{KV_ARTICLE_INDEX}",
                headers={**_auth_headers(), "Content-Type": "application/json"},
                content=json.dumps({"dates": sorted(dates, reverse=True)}),
                timeout=10,
            )
            r.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to write article_index: %s", exc)

        # 期限切れエントリの KV キーを削除
        for old_date in expired:
            try:
                await client.delete(
                    f"{base_url}/{KV_ARTICLE_HISTORY_PREFIX}{old_date}",
                    headers=_auth_headers(),
                    timeout=10,
                )
            except Exception as exc:
                logger.warning("Failed to delete expired article history %s: %s", old_date, exc)

    logger.info("Wrote article history for %s (%d articles)", date, len(flat))


async def append_feedback(action: str, title: str, source: str, url: str) -> None:
    """評価フィードバックを KV の履歴に追記する（Cloudflare Worker から呼び出す想定ではなく、
    テスト・デバッグ用途向けのヘルパー）。
    """
    base_url = _kv_base_url()
    if not base_url:
        return

    prefs = await get_preferences()
    feedback = ArticleFeedback(
        action=action,  # type: ignore[arg-type]
        title=title,
        source=source,
        url=url,
        timestamp=datetime.now(UTC),
    )
    prefs.history.append(feedback)
    # 最大件数を超えた場合は古いものを削除
    if len(prefs.history) > MAX_HISTORY:
        prefs.history = prefs.history[-MAX_HISTORY:]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{base_url}/{KV_PREFERENCES}",
                headers={**_auth_headers(), "Content-Type": "application/json"},
                content=prefs.model_dump_json(),
                timeout=10,
            )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to write preferences to KV: %s", exc)
