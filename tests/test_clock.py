from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.core.clock import JST, jst_today

UTC = ZoneInfo("UTC")


def test_jst_today_default_format() -> None:
    result = jst_today()
    datetime.strptime(result, "%Y-%m-%d")


def test_jst_today_slash_format() -> None:
    result = jst_today("%Y/%m/%d")
    datetime.strptime(result, "%Y/%m/%d")


def test_jst_today_at_utc_2315_returns_next_day() -> None:
    # 23:15 UTC on 2026-06-20 = 08:15 JST on 2026-06-21
    fake_now = datetime(2026, 6, 20, 23, 15, 0, tzinfo=UTC)
    with patch("src.core.clock.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now.astimezone(JST)
        result = jst_today()
    assert result == "2026-06-21"


def test_jst_today_at_utc_2259_returns_same_day() -> None:
    # 22:59 UTC on 2026-06-20 = 07:59 JST on 2026-06-21 — still JST 06-21
    fake_now = datetime(2026, 6, 20, 22, 59, 0, tzinfo=UTC)
    with patch("src.core.clock.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now.astimezone(JST)
        result = jst_today()
    assert result == "2026-06-21"
