from __future__ import annotations

from dataclasses import dataclass

from django.core import signing

from billing.models import BillingProduct, PaymentProvider, ProviderSubscription

PADDLE_CHECKOUT_SALT = "billing.paddle.checkout.v1"
PADDLE_CHECKOUT_REFERENCE_MAX_AGE_SECONDS = 24 * 60 * 60


class PaddleCheckoutUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class PaddleCheckoutPayload:
    price_id: str
    customer_email: str
    checkout_reference: str


def build_paddle_checkout_payload(*, user, product: BillingProduct, environment: str) -> PaddleCheckoutPayload:
    if (
        not product.active
        or product.provider != PaymentProvider.PADDLE
        or product.environment != environment
        or not product.external_price_id
        or product.offer_id is None
    ):
        raise PaddleCheckoutUnavailable("This product is not an active Paddle offer for the selected environment.")
    if (
        product.account_plan_id != product.offer.account_plan_id
        or product.amount_minor != product.offer.amount_minor
        or product.currency != product.offer.currency
        or product.interval != product.offer.interval
        or product.interval_count != product.offer.interval_count
    ):
        raise PaddleCheckoutUnavailable("The Paddle catalog mapping has drifted from the canonical offer.")

    email = str(getattr(user, "email", "") or "").strip()
    if not email:
        raise PaddleCheckoutUnavailable("A verified account email is required for Paddle checkout.")
    if ProviderSubscription.objects.filter(
        user=user,
        status__in=(
            ProviderSubscription.Status.PENDING,
            ProviderSubscription.Status.AUTHORIZED,
            ProviderSubscription.Status.PAUSED,
            ProviderSubscription.Status.PAST_DUE,
        ),
    ).exists():
        raise PaddleCheckoutUnavailable("The account already has a current billing subscription.")

    reference = signing.dumps(
        {
            "user_id": user.pk,
            "product_id": product.pk,
            "offer_code": product.offer.code,
            "environment": environment,
        },
        salt=PADDLE_CHECKOUT_SALT,
        compress=True,
    )
    return PaddleCheckoutPayload(
        price_id=product.external_price_id,
        customer_email=email,
        checkout_reference=reference,
    )


def read_paddle_checkout_reference(value: str) -> dict[str, object]:
    try:
        payload = signing.loads(
            value,
            salt=PADDLE_CHECKOUT_SALT,
            max_age=PADDLE_CHECKOUT_REFERENCE_MAX_AGE_SECONDS,
        )
    except signing.BadSignature as exc:
        raise PaddleCheckoutUnavailable("The Paddle checkout reference is invalid or expired.") from exc
    if not isinstance(payload, dict):
        raise PaddleCheckoutUnavailable("The Paddle checkout reference payload is invalid.")
    return payload
