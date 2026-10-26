from datetime import datetime
from typing import Literal

from ninja import Schema


class NotificationItemData(Schema):
    kind: Literal["proposal", "share", "invitation", "announcement"]
    id: int
    title: str
    body: str
    created_at: datetime
    is_read: bool
    web_url: str
    mobile_path: str


class NotificationListData(Schema):
    items: list[NotificationItemData]
    unread_count: int


class NotificationListEnvelope(Schema):
    ok: Literal[True] = True
    data: NotificationListData
    error: None = None
