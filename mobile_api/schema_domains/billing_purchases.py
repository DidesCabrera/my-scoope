"""Verified purchase responses include the benefits the account can actually use."""

from typing import Literal

from mobile_api.schema_domains.billing import (
    EntitlementsData, EntitlementsEnvelope, SubscriptionData, SubscriptionEnvelope,
)


class SubscriptionPurchaseData(SubscriptionData):
    entitlements: EntitlementsData
    transaction_status: Literal["current", "superseded", "inactive"] = "current"


class SubscriptionPurchaseEnvelope(SubscriptionEnvelope):
    data: SubscriptionPurchaseData


class CreditPackPurchaseData(EntitlementsData):
    purchase_status: Literal["approved", "refunded"]


class CreditPackPurchaseEnvelope(EntitlementsEnvelope):
    data: CreditPackPurchaseData
