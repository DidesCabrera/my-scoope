from __future__ import annotations

from datetime import datetime
from typing import Literal
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
