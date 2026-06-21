from datetime import datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def jst_today(fmt: str = "%Y-%m-%d") -> str:
    return datetime.now(JST).strftime(fmt)
