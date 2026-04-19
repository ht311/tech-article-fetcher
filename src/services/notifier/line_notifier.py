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

from src.core.models import CategoryDef, SelectedArticle

logger = logging.getLogger(__name__)


def _build_article_box(index: int, s: SelectedArticle) -> FlexBox:
    a = s.article

    contents: list[object] = [
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


def _build_category_flex_message(
    cat_name: str,
    selected: list[SelectedArticle],
    global_offset: int,
) -> FlexMessage:
    today = datetime.now().strftime("%Y/%m/%d")
    header_text = f"🗂️ {cat_name} ({today})"

    body_contents: list[object] = [
        FlexText(
            text=header_text,
            weight="bold",
            size="md",
            wrap=True,
        ),
    ]

    for i, s in enumerate(selected, start=global_offset + 1):
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

    return FlexMessage(
        alt_text=f"🗂️ {cat_name} ({today}) — {len(selected)} 件",
        contents=bubble,
    )


async def send_category_messages(
    selections: dict[str, list[SelectedArticle]],
    category_defs: list[CategoryDef],
) -> None:
    """カテゴリごとに LINE Push Message を逐次送信する（category_defs の order 順）。
    0 件カテゴリはスキップする。
    """
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token:
        raise OSError("LINE_CHANNEL_ACCESS_TOKEN is not set")
    if not user_id:
        raise OSError("LINE_USER_ID is not set")

    configuration = Configuration(access_token=token)
    global_offset = 0

    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)

        for cat in category_defs:
            selected = selections.get(cat.id, [])
            if not selected:
                continue

            flex_message = _build_category_flex_message(cat.name, selected, global_offset)
            request = PushMessageRequest(to=user_id, messages=[flex_message])
            api.push_message(request)
            logger.info(
                "LINE message sent: category=%s offset=%d count=%d",
                cat.id, global_offset + 1, len(selected),
            )
            global_offset += len(selected)
