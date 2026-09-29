"""One-time Mercado Pago pack checkout and verified payment settlement."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction

from billing.application.contracts import ProviderPaymentSnapshot
from billing.application.services.credit_packs import (
    CreditPackUnavailable,
    may_buy_credit_packs,
    refund_credit_pack_purchase,
    settle_credit_pack_purchase,
)
from billing.application.services.tax_documents import schedule_tax_document
from billing.models import BillingPayment, PaymentProvider, ProviderCreditPack, TaxDocument

REFERENCE_SALT = "billing.mercado_pago.credit_pack.v1"


def create_credit_pack_checkout(*, user, product: ProviderCreditPack, gateway, back_url: str) -> str:
    if not may_buy_credit_packs(user):
        raise CreditPackUnavailable("credit_pack_paid_plan_required")
    if product.provider != PaymentProvider.MERCADO_PAGO or not product.active or not product.offer.active:
        raise CreditPackUnavailable("credit_pack_product_unavailable")
    email = str(getattr(user, "email", "") or "").strip()
    if not email or not back_url.startswith("https://"):
        raise CreditPackUnavailable("credit_pack_checkout_identity_unavailable")
    reference = signing.dumps(
        {"user_id": user.pk, "product_id": product.pk}, salt=REFERENCE_SALT, compress=True,
    )
    return gateway.create_credit_pack_preference(
        title=f"My Scoope · {product.credits_snapshot} créditos",
        amount_minor=product.amount_minor, currency=product.currency,
        payer_email=email, back_url=back_url, external_reference=reference,
    )


@transaction.atomic
def sync_mercado_pago_credit_pack_payment(snapshot: ProviderPaymentSnapshot) -> BillingPayment:
    if snapshot.provider != PaymentProvider.MERCADO_PAGO or snapshot.external_subscription_id:
        raise CreditPackUnavailable("credit_pack_payment_type_invalid")
    reference = str((snapshot.metadata or {}).get("external_reference") or "")
    try:
        checkout = signing.loads(reference, salt=REFERENCE_SALT)
    except signing.BadSignature as exc:
        raise CreditPackUnavailable("credit_pack_reference_invalid") from exc
    if not isinstance(checkout, dict):
        raise CreditPackUnavailable("credit_pack_reference_invalid")
    user = get_user_model().objects.filter(pk=checkout.get("user_id")).first()
    product = ProviderCreditPack.objects.select_related("offer").filter(
        pk=checkout.get("product_id"), provider=PaymentProvider.MERCADO_PAGO,
    ).first()
    if user is None or product is None:
        raise CreditPackUnavailable("credit_pack_reference_unknown")
    if snapshot.amount_minor != product.amount_minor or snapshot.currency != product.currency:
        raise CreditPackUnavailable("credit_pack_payment_amount_mismatch")
    existing = BillingPayment.objects.select_for_update().filter(
        provider=snapshot.provider, external_payment_id=snapshot.external_payment_id,
    ).first()
    if existing is not None and (existing.user_id != user.pk or existing.subscription_id):
        raise CreditPackUnavailable("credit_pack_payment_owner_mismatch")
    payment, _ = BillingPayment.objects.update_or_create(
        provider=snapshot.provider, external_payment_id=snapshot.external_payment_id,
        defaults={"user": user, "subscription": None, "status": snapshot.status,
                  "amount_minor": snapshot.amount_minor, "currency": snapshot.currency,
                  "approved_at": snapshot.approved_at,
                  "metadata": {"credit_pack_product_id": product.pk, "provider": dict(snapshot.metadata or {})}},
    )
    if snapshot.status == BillingPayment.Status.APPROVED:
        settle_credit_pack_purchase(
            user=user, product=product, external_purchase_id=snapshot.external_payment_id,
            evidence={"source": "mercado_pago_verified_payment", "external_reference": reference},
        )
        schedule_tax_document(payment=payment, request_payload={
            "schema": "myscoope.openfactura_receipt_source.v1", "payment_id": payment.pk,
            "external_payment_id": payment.external_payment_id,
            "amount_minor": payment.amount_minor, "currency": payment.currency,
            "credit_pack_code": product.offer.code,
        })
    elif snapshot.status in {BillingPayment.Status.REFUNDED, BillingPayment.Status.CHARGED_BACK}:
        from billing.models import CreditPackPurchase
        if CreditPackPurchase.objects.filter(
            provider=snapshot.provider, external_purchase_id=snapshot.external_payment_id,
        ).exists():
            refund_credit_pack_purchase(
                provider=snapshot.provider, external_purchase_id=snapshot.external_payment_id,
            )
        TaxDocument.objects.filter(payment=payment).update(
            adjustment_required=True,
            adjustment_reason=f"Tax review required after payment status {payment.status}.",
        )
    return payment
