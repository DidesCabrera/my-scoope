from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from ninja import Schema


class ShareResourceCreateInput(Schema):
    claim_policy: Literal["none", "single", "multiple"] = "multiple"


class ShareResourceData(Schema):
    id: UUID
    subject_type: Literal["daily_plan", "food", "meal", "program"]
    title: str
    public_url: str
    claim_policy: Literal["none", "single", "multiple"]
    status: Literal["active", "revoked", "expired"]
    created_at: datetime


class ShareResourceEnvelope(Schema):
    ok: Literal[True] = True
    data: ShareResourceData
    error: None = None


class PublicShareResourceData(Schema):
    id: UUID
    subject_type: Literal["daily_plan", "food", "meal", "program"]
    title: str
    claim_policy: Literal["none", "single", "multiple"]
    snapshot: dict[str, Any]


class PublicShareResourceEnvelope(Schema):
    ok: Literal[True] = True
    data: PublicShareResourceData
    error: None = None


class ShareClaimData(Schema):
    resource_id: UUID
    inbox_item_id: int


class ShareClaimEnvelope(Schema):
    ok: Literal[True] = True
    data: ShareClaimData
    error: None = None


class SharingInboxItemData(Schema):
    id: int
    resource_id: UUID
    subject_type: Literal["daily_plan", "food", "meal", "program"]
    title: str
    sender: str
    public_url: str
    is_read: bool
    is_favorite: bool
    is_saved: bool
    created_at: datetime


class SharingInboxData(Schema):
    items: list[SharingInboxItemData]
    count: int


class SharingInboxEnvelope(Schema):
    ok: Literal[True] = True
    data: SharingInboxData
    error: None = None


class SharingInboxUpdateInput(Schema):
    is_read: bool | None = None
    is_favorite: bool | None = None
    dismissed: bool | None = None


class SharingInboxItemEnvelope(Schema):
    ok: Literal[True] = True
    data: SharingInboxItemData
    error: None = None


class SharingInboxSaveData(Schema):
    entity: Literal["dailyPlan", "food", "meal", "program"]
    item_id: int


class SharingInboxSaveEnvelope(Schema):
    ok: Literal[True] = True
    data: SharingInboxSaveData
    error: None = None
