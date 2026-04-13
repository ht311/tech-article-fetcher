import logging
import os
from datetime import datetime

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexBox,
    FlexBubble,
    FlexButton,
    FlexImage,
    FlexMessage,
    FlexSeparator,
    FlexText,
    MessageAction,
    MessagingApi,
    PushMessageRequest,
    URIAction,
)

from src.models import SelectedArticle

logger = logging.getLogger(__name__)

# 縦並びレイアウトの最大記事数
_MAX_ARTICLES = 10


def _build_article_box(index: int, s: SelectedArticle) -> FlexBox:
    """1記事分の縦並び FlexBox を生成する。サムネイルがあれば表示する。"""
    a = s.article

    contents: list = [
        FlexBox(
            layout="horizontal",
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
        ),
    ]

    # サムネイル画像があれば挿入
    thumbnail_url = getattr(a, "thumbnail_url", None)
    if thumbnail_url:
        contents.append(
            FlexImage(
                url=thumbnail_url,
                size="full",
                aspect_ratio="20:13",
                aspect_mode="cover",
            )
        )

    contents += [
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
                FlexButton(
                    action=URIAction(label="🔗 読む", uri=str(a.url)),
                    style="link",
                    height="sm",
                    flex=1,
                ),
            ],
        ),
    ]

    return FlexBox(
        layout="vertical",
        spacing="sm",
        contents=contents,
    )


def _is_fallback(selected: list[SelectedArticle]) -> bool:
    """フォールバック選定かどうかを reason フィールドで判定する。"""
    return any("フォールバック" in s.reason for s in selected)


def _build_flex_message(selected: list[SelectedArticle]) -> FlexMessage:
    """記事リストから縦並び Flex Message を生成する。"""
    today = datetime.now().strftime("%Y/%m/%d")
    fallback = _is_fallback(selected)

    header_text = f"📚 今日の技術記事 ({today})"
    if fallback:
        header_text += " ⚠️ AI選定不可・最新順"

    body_contents: list = [
        FlexText(
            text=header_text,
            weight="bold",
            size="md",
            wrap=True,
            color="#CC0000" if fallback else "#000000",
        ),
    ]

    for i, s in enumerate(selected, start=1):
        body_contents.append(FlexSeparator(margin="md"))
        body_contents.append(_build_article_box(i, s))

    bubble = FlexBubble(
        size="giga",
        body=FlexBox(
            layout="vertical",
            spacing="md",
            contents=body_contents,
        ),
    )

    alt_suffix = "（AI選定不可）" if fallback else ""
    return FlexMessage(
        alt_text=f"📚 今日の技術記事 ({today}){alt_suffix} — {len(selected)} 件",
        contents=bubble,
    )


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

    display = selected[:_MAX_ARTICLES]
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
