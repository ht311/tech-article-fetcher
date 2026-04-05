import logging
import os
from datetime import datetime

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)

from src.models import SelectedArticle

logger = logging.getLogger(__name__)


def _build_message_text(selected: list[SelectedArticle]) -> str:
    """選定記事リストを LINE 送信用のテキストに整形する。"""
    today = datetime.now().strftime("%Y/%m/%d")
    lines = [f"📚 今日の技術記事 ({today})\n"]
    for i, s in enumerate(selected, start=1):
        a = s.article
        lines.append(f"{i}. [{a.source}] {a.title}\n   → {s.reason}\n   🔗 {a.url}")
    return "\n\n".join(lines)


async def send_line_message(selected: list[SelectedArticle]) -> None:
    """LINE Messaging API の Push Message で指定ユーザーに記事を送信する。
    環境変数 LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID が必須。
    """
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token:
        raise EnvironmentError("LINE_CHANNEL_ACCESS_TOKEN is not set")
    if not user_id:
        raise EnvironmentError("LINE_USER_ID is not set")

    text = _build_message_text(selected)
    configuration = Configuration(access_token=token)

    # ApiClient はコンテキストマネージャーで HTTP セッションを管理する
    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        request = PushMessageRequest(
            to=user_id,
            messages=[TextMessage(type="text", text=text)],
        )
        api.push_message(request)

    logger.info("LINE push message sent to %s", user_id)
