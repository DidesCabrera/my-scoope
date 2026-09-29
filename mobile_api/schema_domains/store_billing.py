from datetime import datetime

from ninja import Schema


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


class CreditPackProductData(Schema):
    product_id: str
    provider: str
    credits: int
    amount_minor: int
    currency: str
