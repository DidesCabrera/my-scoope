from __future__ import annotations

from django.db import transaction

from billing.application.contracts import ProviderPaymentSnapshot, ProviderSubscriptionSnapshot
from billing.application.services.projections import project_provider_subscription
from billing.application.services.tax_documents import schedule_tax_document
from billing.models import BillingPayment, ProviderSubscription, TaxDocument


class UnknownBillingResource(LookupError):
    pass


class BillingResourceMismatch(ValueError):
    pass


@transaction.atomic
def sync_provider_subscription(snapshot: ProviderSubscriptionSnapshot) -> ProviderSubscription:
    subscription = (
        ProviderSubscription.objects.select_for_update()
        .select_related("product", "product__account_plan", "user")
        .filter(provider=snapshot.provider, external_subscription_id=snapshot.external_subscription_id)
        .first()
    )
    if subscription is None:
        raise UnknownBillingResource("The provider subscription is not registered in My Scoope.")
    if snapshot.external_product_id and snapshot.external_product_id != subscription.product.external_product_id:
        raise BillingResourceMismatch("The provider product does not match the registered billing product.")

    subscription.status = snapshot.status
    subscription.current_period_start = snapshot.current_period_start
    subscription.current_period_end = snapshot.current_period_end
    metadata = dict(subscription.metadata or {})
    metadata["provider_snapshot"] = dict(snapshot.metadata or {})
    subscription.metadata = metadata
    subscription.save(
        update_fields=["status", "current_period_start", "current_period_end", "metadata", "updated_at"]
    )
    project_provider_subscription(subscription)
    return subscription


@transaction.atomic
def sync_provider_payment(snapshot: ProviderPaymentSnapshot) -> BillingPayment:
    subscription = (
        ProviderSubscription.objects.select_for_update()
        .select_related("product", "user")
        .filter(provider=snapshot.provider, external_subscription_id=snapshot.external_subscription_id)
        .first()
    )
    if subscription is None:
        raise UnknownBillingResource("The payment does not belong to a registered provider subscription.")

    payment, _ = BillingPayment.objects.update_or_create(
        provider=snapshot.provider,
        external_payment_id=snapshot.external_payment_id,
        defaults={
            "user": subscription.user,
            "subscription": subscription,
            "status": snapshot.status,
            "amount_minor": snapshot.amount_minor,
            "currency": snapshot.currency,
            "approved_at": snapshot.approved_at,
            "metadata": dict(snapshot.metadata or {}),
        },
    )
    if payment.status == BillingPayment.Status.APPROVED:
        schedule_tax_document(
            payment=payment,
            request_payload={
                "schema": "myscoope.openfactura_receipt_source.v1",
                "payment_id": payment.pk,
                "external_payment_id": payment.external_payment_id,
                "amount_minor": payment.amount_minor,
                "currency": payment.currency,
                "plan_slug": subscription.product.account_plan.slug,
            },
        )
    elif payment.status in {BillingPayment.Status.REFUNDED, BillingPayment.Status.CHARGED_BACK}:
        subscription.status = ProviderSubscription.Status.PAST_DUE
        subscription.save(update_fields=["status", "updated_at"])
        project_provider_subscription(subscription)
        TaxDocument.objects.filter(payment=payment).update(
            adjustment_required=True,
            adjustment_reason=f"Tax review required after payment status {payment.status}.",
        )
    return payment
