from datetime import datetime
from typing import Literal

from ninja import Field, Schema


class AppleTransactionInput(Schema):
    signed_transaction: str = Field(min_length=20, max_length=20000)
    product_id: str = Field(default="", max_length=160)


class SubscriptionProductData(Schema):
    product_id: str
    provider: str
    base_plan_id: str = ""
    plan_name: str
    interval: str


class SubscriptionEvidenceData(Schema):
    provider: str
    status: str
    period_end: datetime | None = None
    product_id: str = ""
    next_product_id: str = ""
    cancel_at_period_end: bool = False


class CreditPackProductData(Schema):
    product_id: str
    provider: str
    credits: int
    amount_minor: int
    currency: str


class TransactionProductData(Schema):
    product_id: str
    provider: str
    kind: Literal["subscription", "credit_pack"]
    plan_name: str = ""
