from __future__ import annotations

from dataclasses import dataclass

from django.core import signing
from django.db import transaction

from billing.application.contracts import PaymentGateway
from billing.application.services.provider_sync import (
    BillingResourceMismatch,
    sync_provider_subscription,
)
from billing.models import BillingProduct, PaymentProvider, ProviderSubscription


class BillingCheckoutUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class BillingCheckout:
    subscription: ProviderSubscription
    checkout_url: str


def create_subscription_checkout(
    *,
    user,
    product: BillingProduct,
    gateway: PaymentGateway,
    back_url: str,
) -> BillingCheckout:
    if not product.active or product.provider != PaymentProvider.MERCADO_PAGO:
        raise BillingCheckoutUnavailable("This billing product is not available for Mercado Pago checkout.")
    payer_email = str(getattr(user, "email", "") or "").strip()
    if not payer_email:
        raise BillingCheckoutUnavailable("A verified account email is required for checkout.")
    if ProviderSubscription.objects.filter(
        user=user,
        status__in=(
            ProviderSubscription.Status.PENDING,
            ProviderSubscription.Status.AUTHORIZED,
            ProviderSubscription.Status.PAUSED,
            ProviderSubscription.Status.PAST_DUE,
        ),
    ).exists():
        raise BillingCheckoutUnavailable("The account already has a current billing subscription.")

    external_reference = signing.dumps(
        {"user_id": user.pk, "product_id": product.pk},
        salt="billing.mercado_pago.checkout.v1",
        compress=True,
    )
    result = gateway.create_subscription(
        external_product_id=product.external_product_id,
        payer_email=payer_email,
        back_url=back_url,
        external_reference=external_reference,
    )
    if result.subscription.provider != product.provider:
        raise BillingResourceMismatch("The checkout provider does not match the selected product.")
    if result.subscription.external_product_id and result.subscription.external_product_id != product.external_product_id:
        raise BillingResourceMismatch("The checkout product does not match the selected product.")

    with transaction.atomic():
        subscription, _ = ProviderSubscription.objects.update_or_create(
            provider=result.subscription.provider,
            external_subscription_id=result.subscription.external_subscription_id,
            defaults={
                "user": user,
                "product": product,
                "status": result.subscription.status,
                "current_period_start": result.subscription.current_period_start,
                "current_period_end": result.subscription.current_period_end,
                "metadata": {
                    "checkout_url": result.checkout_url,
                    "external_reference": external_reference,
                    "provider_snapshot": dict(result.subscription.metadata or {}),
                },
            },
        )
        sync_provider_subscription(result.subscription)
    return BillingCheckout(subscription=subscription, checkout_url=result.checkout_url)


def cancel_user_subscription(*, user, subscription: ProviderSubscription, gateway: PaymentGateway) -> ProviderSubscription:
    if subscription.user_id != user.pk:
        raise BillingCheckoutUnavailable("The billing subscription does not belong to this account.")
    if subscription.status in {ProviderSubscription.Status.CANCELED, ProviderSubscription.Status.EXPIRED}:
        return subscription
    snapshot = gateway.cancel_subscription(subscription.external_subscription_id)
    return sync_provider_subscription(snapshot)
