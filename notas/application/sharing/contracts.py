"""Stable vocabulary for the Sharing bounded context."""

from enum import StrEnum

SHARE_SNAPSHOT_SCHEMA_VERSION = "sharing.snapshot.v1"


class ShareSubjectType(StrEnum):
    DAILY_PLAN = "daily_plan"
    FOOD = "food"
    MEAL = "meal"
    PROGRAM = "program"


class ShareVisibility(StrEnum):
    UNLISTED = "unlisted"


class ShareClaimPolicy(StrEnum):
    NONE = "none"
    SINGLE = "single"
    MULTIPLE = "multiple"


class ShareResourceStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ShareInvitationStatus(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    CLAIMED = "claimed"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ShareClaimSource(StrEnum):
    EMAIL = "email"
    LINK = "link"
