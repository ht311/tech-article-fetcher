import logging
import os
from datetime import datetime

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexBox,
    FlexBubble,
    FlexButton,
    FlexCarousel,
    FlexMessage,
    FlexText,
    MessageAction,
    MessagingApi,
    PushMessageRequest,
    URIAction,
)

from src.models import SelectedArticle

logger = logging.getLogger(__name__)

# LINE Flex Message カルーセルの最大バブル数
_MAX_CAROUSEL_BUBBLES = 10


def _build_article_bubble(index: int, s: SelectedArticle) -> FlexBubble:
    """1記事分の Flex Bubble カードを生成する。"""
    a = s.article

    header = FlexBox(
        layout="horizontal",
        background_color="#f0f0f0",
        padding_all="sm",
        contents=[
            FlexText(
                text=f"#{index}",
                weight="bold",
                color="#1DB446",
                flex=0,
                size="sm",
            ),
            FlexText(
                text=a.source,
                color="#888888",
                size="sm",
                align="end",
            ),
        ],
    )

    body = FlexBox(
        layout="vertical",
        spacing="sm",
        contents=[
            FlexText(
                text=a.title,
                weight="bold",
                wrap=True,
                size="sm",
            ),
            FlexText(
                text=s.reason,
                color="#888888",
                wrap=True,
                size="xs",
            ),
        ],
    )

    footer = FlexBox(
        layout="vertical",
        spacing="sm",
        contents=[
            FlexBox(
                layout="horizontal",
                spacing="sm",
                contents=[
                    FlexButton(
                        action=MessageAction(label="👍 Good", text=f"👍{index}"),
                        style="primary",
                        height="sm",
                        flex=1,
                    ),
                    FlexButton(
                        action=MessageAction(label="👎 Bad", text=f"👎{index}"),
                        style="secondary",
                        height="sm",
                        flex=1,
                    ),
                ],
            ),
            FlexButton(
                action=URIAction(label="🔗 読む", uri=str(a.url)),
                style="link",
                height="sm",
            ),
        ],
    )

    return FlexBubble(
        size="kilo",
        header=header,
        body=body,
        footer=footer,
    )


def _build_flex_message(selected: list[SelectedArticle]) -> FlexMessage:
    """記事リストから Flex Message カルーセルを生成する。"""
    today = datetime.now().strftime("%Y/%m/%d")
    bubbles = [_build_article_bubble(i, s) for i, s in enumerate(selected, start=1)]
    return FlexMessage(
        alt_text=f"📚 今日の技術記事 ({today}) — {len(selected)} 件",
        contents=FlexCarousel(contents=bubbles),
    )


async def send_line_message(selected: list[SelectedArticle]) -> None:
    """LINE Messaging API の Push Message で指定ユーザーに記事を送信する。
    Flex Message カルーセル形式で各記事カードに 👍/👎 ボタンと URL リンクを付与する。
    環境変数 LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID が必須。
    """
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token:
        raise EnvironmentError("LINE_CHANNEL_ACCESS_TOKEN is not set")
    if not user_id:
        raise EnvironmentError("LINE_USER_ID is not set")

    display = selected[:_MAX_CAROUSEL_BUBBLES]
    flex_message = _build_flex_message(display)

    configuration = Configuration(access_token=token)

    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        request = PushMessageRequest(
            to=user_id,
            messages=[flex_message],
        )
        api.push_message(request)

    logger.info("LINE flex message sent to %s (%d articles)", user_id, len(display))
