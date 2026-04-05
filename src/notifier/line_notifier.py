import logging
import os
from datetime import datetime

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessageAction,
    MessagingApi,
    PushMessageRequest,
    QuickReply,
    QuickReplyItem,
    TextMessage,
)

from src.config import MAX_ARTICLES_WITH_QUICKREPLY
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


def _build_quick_reply(count: int) -> QuickReply:
    """記事数分の 👍N / 👎N Quick Reply ボタンを生成する。
    LINE の制約: 最大 13 アイテム。count を MAX_ARTICLES_WITH_QUICKREPLY 以下にすること。
    """
    items = []
    for i in range(1, count + 1):
        items.append(
            QuickReplyItem(action=MessageAction(label=f"👍{i}", text=f"👍{i}"))
        )
        items.append(
            QuickReplyItem(action=MessageAction(label=f"👎{i}", text=f"👎{i}"))
        )
    return QuickReply(items=items)


async def send_line_message(selected: list[SelectedArticle]) -> None:
    """LINE Messaging API の Push Message で指定ユーザーに記事を送信する。
    記事数を MAX_ARTICLES_WITH_QUICKREPLY 以下に絞り、Quick Reply ボタンを付与する。
    環境変数 LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID が必須。
    """
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token:
        raise EnvironmentError("LINE_CHANNEL_ACCESS_TOKEN is not set")
    if not user_id:
        raise EnvironmentError("LINE_USER_ID is not set")

    # Quick Reply の上限に合わせて記事数を制限する
    display = selected[:MAX_ARTICLES_WITH_QUICKREPLY]

    text = _build_message_text(display)
    quick_reply = _build_quick_reply(len(display))

    configuration = Configuration(access_token=token)

    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        request = PushMessageRequest(
            to=user_id,
            messages=[TextMessage(type="text", text=text, quick_reply=quick_reply)],
        )
        api.push_message(request)

    logger.info("LINE push message sent to %s (%d articles with quick reply)", user_id, len(display))
