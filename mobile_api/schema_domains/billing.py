from __future__ import annotations

from datetime import datetime
from typing import Literal

from ninja import Field, Schema


class EntitlementsData(Schema):
    plan_name: str
    plan_slug: str
    subscription_status: str
    period: str
    available_credits: int
    reserved_credits: int
    monthly_credit_limit: int
    daily_credit_limit: int


class EntitlementsEnvelope(Schema):
    ok: Literal[True] = True
    data: EntitlementsData
    error: None = None


class AppleSubscriptionProductData(Schema):
    product_id: str
    plan_name: str
    interval: str


class SubscriptionEvidenceData(Schema):
    provider: str
    status: str
    period_end: datetime | None = None


class SubscriptionData(Schema):
    eligible: bool
    purchases_enabled: bool
    app_account_token: str
    plan_name: str
    status: str
    products: list[AppleSubscriptionProductData]
    evidence: list[SubscriptionEvidenceData]
    duplicate_active_providers: bool


class SubscriptionEnvelope(Schema):
    ok: Literal[True] = True
    data: SubscriptionData
    error: None = None


class AppleTransactionInput(Schema):
    signed_transaction: str = Field(min_length=20, max_length=20000)
