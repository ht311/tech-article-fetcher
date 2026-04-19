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

from src.config import CATEGORIES
from src.models import SelectedArticle

logger = logging.getLogger(__name__)

_MAX_ARTICLES_PER_CATEGORY = 5


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
    """カテゴリ名・記事リスト・グローバルオフセットから Flex Message を生成する。
    記事インデックスは global_offset+1 から始まり、Cloudflare Worker の last_articles キーと一致する。
    """
    today = datetime.now().strftime("%Y/%m/%d")
    header_text = f"🗂️ {cat_name} ({today})"

    body_contents: list = [
        FlexText(
            text=header_text,
            weight="bold",
            size="md",
            wrap=True,
        ),
    ]

    display = selected[:_MAX_ARTICLES_PER_CATEGORY]
    for i, s in enumerate(display, start=global_offset + 1):
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
        alt_text=f"🗂️ {cat_name} ({today}) — {len(display)} 件",
        contents=bubble,
    )


async def send_category_messages(selections: dict[str, list[SelectedArticle]]) -> None:
    """カテゴリごとに LINE Push Message を逐次送信する（CATEGORIES 順で順序を保証）。
    0 件カテゴリはスキップする。記事インデックスはカテゴリをまたいでグローバル連番になる。
    """
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token:
        raise EnvironmentError("LINE_CHANNEL_ACCESS_TOKEN is not set")
    if not user_id:
        raise EnvironmentError("LINE_USER_ID is not set")

    configuration = Configuration(access_token=token)
    global_offset = 0

    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)

        for cat in CATEGORIES:
            cat_id: str = cat["id"]
            cat_name: str = cat["name"]
            selected = selections.get(cat_id, [])
            if not selected:
                continue

            flex_message = _build_category_flex_message(cat_name, selected, global_offset)
            request = PushMessageRequest(to=user_id, messages=[flex_message])
            api.push_message(request)
            logger.info(
                "LINE message sent: category=%s offset=%d count=%d",
                cat_id, global_offset + 1, len(selected),
            )
            global_offset += len(selected[:_MAX_ARTICLES_PER_CATEGORY])
