from __future__ import annotations

from typing import Literal

from ninja import Schema

from mobile_api.schema_domains.store_billing import (
    CreditPackProductData,
    SubscriptionEvidenceData,
    SubscriptionProductData,
    TransactionProductData,
)


class EntitlementsData(Schema):
    plan_name: str
    plan_slug: str
    subscription_status: str
    period: str
    available_credits: int
    credit_status: Literal["ready", "pending_reservation", "frozen"] = "ready"
    reserved_credits: int
    monthly_credit_limit: int
    daily_credit_limit: int
    included_monthly_credits: int = 0
    purchased_credits: int = 0
    workspace_limits: dict[str, int | None] = {}
    workspace_usage: dict[str, int] = {}


class EntitlementsEnvelope(Schema):
    ok: Literal[True] = True
    data: EntitlementsData
    error: None = None


class SubscriptionData(Schema):
    eligible: bool
    purchases_enabled: bool
    app_account_token: str
    plan_name: str
    status: str
    google_obfuscated_account_id: str
    products: list[SubscriptionProductData]
    evidence: list[SubscriptionEvidenceData]
    duplicate_active_providers: bool
    credit_packs: list[CreditPackProductData] = []
    can_buy_credit_packs: bool = False
    transaction_products: list[TransactionProductData] = []


class SubscriptionEnvelope(Schema):
    ok: Literal[True] = True
    data: SubscriptionData
    error: None = None
