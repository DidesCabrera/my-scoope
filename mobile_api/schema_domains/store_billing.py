from ninja import Schema


class SubscriptionProductData(Schema):
    product_id: str
    provider: str
    base_plan_id: str = ""
    plan_name: str
    interval: str
