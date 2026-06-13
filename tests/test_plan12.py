"""plan-12 の新規機能テスト。

- Java 専門ソースが important=True で default_sources() に含まれる
- merge_conferences: append-only マージ・重複は last_seen_at 更新のみ
- get_recent_sent_urls: index + 日別履歴から URL 集合を返す（httpx mock）
- conference_fetcher: 固定 HTML から title/url 抽出・is_important 付与・時間フィルタ
- SpeakerDeck フィルタ緩和: PREFERRED_TOPICS 一致の英語スライドが通る
- ピン留め: Gemini が落とした重要記事がカテゴリ先頭に挿入される
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from src.core.config import default_sources
from src.core.models import Article, CategoryDef, Conference, ConferenceList, SelectedArticle
from src.services.fetchers.speakerdeck_fetcher import _is_relevant
from src.services.storage.preferences import merge_conferences

# --- Java 専門ソース ---

def test_important_sources_in_default_sources():
    sources = default_sources()
    important = [s for s in sources if s.get("important")]
    names = {s["name"] for s in important}
    assert "Inside.java" in names
    assert "InfoQ Java" in names


def test_important_sources_are_rss():
    sources = default_sources()
    for s in sources:
        if s.get("important"):
            assert s["type"] == "rss"


# --- merge_conferences ---

def _conf(name: str, days_ago: int = 1) -> Conference:
    t = datetime.now(UTC) - timedelta(days=days_ago)
    return Conference(name=name, added_at=t, last_seen_at=t)


def test_merge_conferences_appends_new():
    existing = ConferenceList(conferences=[_conf("JJUG CCC")])
    result = merge_conferences(existing, ["JAWS DAYS", "TSKaigi"])
    names = {c.name for c in result.conferences}
    assert "JJUG CCC" in names
    assert "JAWS DAYS" in names
    assert "TSKaigi" in names


def test_merge_conferences_no_duplicate():
    existing = ConferenceList(conferences=[_conf("JJUG CCC")])
    result = merge_conferences(existing, ["JJUG CCC", "jjug ccc"])
    jjug_entries = [c for c in result.conferences if "jjug" in c.name.lower()]
    assert len(jjug_entries) == 1


def test_merge_conferences_updates_last_seen():
    old_time = datetime.now(UTC) - timedelta(days=10)
    existing = ConferenceList(
        conferences=[Conference(name="JJUG CCC", added_at=old_time, last_seen_at=old_time)]
    )
    result = merge_conferences(existing, ["JJUG CCC"])
    jjug = next(c for c in result.conferences if c.name == "JJUG CCC")
    assert jjug.last_seen_at is not None
    assert jjug.last_seen_at > old_time


def test_merge_conferences_ignores_empty_strings():
    existing = ConferenceList()
    result = merge_conferences(existing, ["", "  ", "JJUG CCC"])
    assert len(result.conferences) == 1


# --- SpeakerDeck フィルタ緩和 ---

def test_is_relevant_japanese():
    assert _is_relevant("Javaの最新情報") is True


def test_is_relevant_preferred_topic_english():
    # "Java" は PREFERRED_TOPICS に含まれるので英語でも通る
    assert _is_relevant("JJUG CCC Spring 2025 - Java 26 Features") is True


def test_is_relevant_spring_boot_english():
    assert _is_relevant("Spring Boot 4 Migration Guide") is True


def test_is_relevant_unrelated_english():
    assert _is_relevant("My random presentation about cooking") is False


# --- ピン留め ---

def _make_article(url: str, important: bool = False, days_ago: int = 0) -> Article:
    return Article(
        title=f"Article {url}",
        url=url,
        source="TestSource",
        published_at=datetime.now(UTC) - timedelta(days=days_ago),
        is_important=important,
    )


def _make_selected(article: Article) -> SelectedArticle:
    return SelectedArticle(article=article, reason="test", category_id="backend")


def test_pin_important_inserts_at_front():
    from src.cli.main import _pin_important

    normal = _make_article("https://example.com/normal")
    important = _make_article("https://example.com/important", important=True)

    cat = CategoryDef(id="backend", name="バックエンド", keywords=["java"])
    buckets = {"backend": [normal, important]}
    selections = {"backend": [_make_selected(normal)]}

    result = _pin_important(selections, buckets, [cat], max_pins=2)
    assert result["backend"][0].article.url == important.url


def test_pin_important_no_duplicate():
    from src.cli.main import _pin_important

    important = _make_article("https://example.com/important", important=True)

    cat = CategoryDef(id="backend", name="バックエンド", keywords=["java"])
    buckets = {"backend": [important]}
    # Gemini がすでに選んでいる場合
    selections = {"backend": [_make_selected(important)]}

    result = _pin_important(selections, buckets, [cat], max_pins=2)
    urls = [str(s.article.url) for s in result["backend"]]
    assert urls.count(str(important.url)) == 1


def test_pin_important_respects_max_pins():
    from src.cli.main import _pin_important

    importants = [_make_article(f"https://example.com/imp{i}", important=True) for i in range(5)]
    cat = CategoryDef(id="backend", name="バックエンド", keywords=["java"])
    buckets = {"backend": importants}
    selections: dict[str, list[SelectedArticle]] = {"backend": []}

    result = _pin_important(selections, buckets, [cat], max_pins=2)
    assert len(result["backend"]) == 2


# --- get_recent_sent_urls (httpx mock) ---

@pytest.mark.asyncio
async def test_get_recent_sent_urls_returns_urls(monkeypatch):
    from src.services.storage.preferences import get_recent_sent_urls

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    index_data = {"dates": [today]}
    history_data = [{"url": "https://example.com/article1"}, {"url": "https://example.com/article2"}]

    call_count = 0

    class MockResponse:
        status_code = 200

        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self._data

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def get(self, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "article_index" in url:
                return MockResponse(index_data)
            return MockResponse(history_data)

    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_KV_NAMESPACE_ID", "test-ns")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")

    with patch("src.services.storage.preferences.httpx.AsyncClient", MockClient):
        urls = await get_recent_sent_urls(days=7)

    assert "https://example.com/article1" in urls
    assert "https://example.com/article2" in urls


# --- conference_fetcher HTML パース ---

SPEAKERDECK_HTML = """
<html><body>
<div class="speakerdeck-talk">
  <a href="/alice/java26-features"><h3>Java 26 Features</h3></a>
  <time datetime="2026-06-01T00:00:00Z">June 1, 2026</time>
</div>
<div class="speakerdeck-talk">
  <a href="/bob/spring-boot-tips"><h3>Spring Boot Tips</h3></a>
</div>
</body></html>
"""

DOCSWELL_HTML = """
<html><body>
<div class="slide-card">
  <h3><a href="/slides/jjug-ccc-2026">JJUG CCC 2026 まとめ</a></h3>
  <time datetime="2026-06-05T00:00:00Z">2026-06-05</time>
</div>
</body></html>
"""


@pytest.mark.asyncio
async def test_conference_fetcher_extracts_slides():
    from src.services.fetchers.conference_fetcher import (
        _parse_docswell_html,
        _parse_speakerdeck_html,
    )

    conf_name = "JJUG CCC"
    sd_articles = _parse_speakerdeck_html(SPEAKERDECK_HTML, f"SpeakerDeck:{conf_name}")
    dw_articles = _parse_docswell_html(DOCSWELL_HTML, f"Docswell:{conf_name}")

    assert len(sd_articles) >= 1
    assert all(a.is_important for a in sd_articles)
    assert any("Java 26" in a.title for a in sd_articles)

    assert len(dw_articles) >= 1
    assert all(a.is_important for a in dw_articles)
    assert any("JJUG" in a.title for a in dw_articles)


@pytest.mark.asyncio
async def test_conference_fetcher_time_filter():
    from src.services.fetchers.conference_fetcher import fetch_conference_slides

    conf = Conference(name="JJUG CCC", added_at=datetime.now(UTC))
    old_date = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    html_old = f"""
    <html><body>
    <div class="speakerdeck-talk">
      <a href="/alice/old-talk"><h3>Old Talk</h3></a>
      <time datetime="{old_date}">{old_date}</time>
    </div>
    </body></html>
    """

    class MockResp:
        status_code = 200
        text = html_old

        def raise_for_status(self):
            pass

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def get(self, url, **kwargs):
            return MockResp()

    mock_target = "src.services.fetchers.conference_fetcher.httpx.AsyncClient"
    with patch(mock_target, return_value=MockClient()):
        # 1時間ウィンドウ → 30日前の記事は除外される
        articles = await fetch_conference_slides([conf], hours=1)

    assert len(articles) == 0
