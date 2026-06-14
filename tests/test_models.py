from datetime import UTC, datetime

from src.core.models import ArticleFeedback, UserPreferences


def _make_feedback(action: str, title: str, source: str = "Zenn") -> ArticleFeedback:
    return ArticleFeedback(
        action=action,  # type: ignore[arg-type]
        title=title,
        source=source,
        url=f"https://example.com/{title}",
        timestamp=datetime.now(UTC),
    )


def test_get_summary_empty_history() -> None:
    prefs = UserPreferences()
    assert prefs.get_summary() == ""
    assert prefs.get_summary(known_topics=["java"]) == ""


def test_get_summary_source_aggregation() -> None:
    prefs = UserPreferences(history=[
        _make_feedback("good", "Java 記事", "Zenn"),
        _make_feedback("good", "Spring Boot 記事", "Zenn"),
        _make_feedback("bad", "入門記事", "はてブIT"),
    ])
    summary = prefs.get_summary()
    assert "高評価したソース" in summary
    assert "Zenn" in summary
    assert "低評価したソース" in summary
    assert "はてブIT" in summary
    assert "高評価したトピック" not in summary  # known_topics なしはトピック集計しない


def test_get_summary_topic_aggregation_good() -> None:
    prefs = UserPreferences(history=[
        _make_feedback("good", "Rust で作る高速APIサーバー"),
        _make_feedback("good", "Rust と WebAssembly の組み合わせ"),
        _make_feedback("good", "TypeScript 5.5 の新機能"),
    ])
    summary = prefs.get_summary(known_topics=["rust", "typescript", "java"])
    assert "高評価したトピック" in summary
    assert "rust" in summary


def test_get_summary_topic_aggregation_bad() -> None:
    prefs = UserPreferences(history=[
        _make_feedback("bad", "入門 Python チュートリアル"),
        _make_feedback("bad", "Python で始めるデータ分析"),
    ])
    summary = prefs.get_summary(known_topics=["python", "rust"])
    assert "低評価したトピック" in summary
    assert "python" in summary


def test_get_summary_no_topic_match() -> None:
    """タイトルに語彙語が含まれない場合はトピック行が出ない。"""
    prefs = UserPreferences(history=[
        _make_feedback("good", "アーキテクチャ設計の話"),
    ])
    summary = prefs.get_summary(known_topics=["java", "rust"])
    assert "高評価したトピック" not in summary


def test_get_summary_known_topics_none_is_backward_compatible() -> None:
    """known_topics=None でも従来のソース集計だけが返る。"""
    prefs = UserPreferences(history=[
        _make_feedback("good", "Java 記事", "Zenn"),
    ])
    summary_default = prefs.get_summary()
    summary_none = prefs.get_summary(known_topics=None)
    assert summary_default == summary_none
    assert "高評価したトピック" not in summary_none


def test_get_summary_ends_with_diversity_note() -> None:
    prefs = UserPreferences(history=[_make_feedback("good", "Java 記事")])
    summary = prefs.get_summary()
    assert "多様性も維持" in summary
