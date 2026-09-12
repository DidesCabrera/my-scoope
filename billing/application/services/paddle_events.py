from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.dateparse import parse_datetime

from billing.application.contracts import ProviderPaymentSnapshot
from billing.application.services.events import claim_billing_event, finish_billing_event
from billing.application.services.paddle_checkout import (
    PaddleCheckoutUnavailable,
    read_paddle_checkout_reference,
)
from billing.application.services.projections import project_provider_subscription
from billing.application.services.provider_sync import sync_provider_payment
from billing.models import (
    BillingEvent,
    BillingPayment,
    BillingProduct,
    PaymentProvider,
    ProviderSubscription,
)


class PaddleEventError(ValueError):
    pass


_SUBSCRIPTION_STATUS_MAP = {
    "trialing": ProviderSubscription.Status.AUTHORIZED,
    "active": ProviderSubscription.Status.AUTHORIZED,
    "past_due": ProviderSubscription.Status.PAST_DUE,
    "paused": ProviderSubscription.Status.PAUSED,
    "canceled": ProviderSubscription.Status.CANCELED,
}

_TRANSACTION_STATUS_MAP = {
    "paid": "approved",
    "completed": "approved",
    "past_due": "rejected",
    "canceled": "canceled",
    "ready": "pending",
    "billed": "pending",
}


def process_paddle_event(*, event: BillingEvent, environment: str) -> BillingEvent:
    claimed = claim_billing_event(event.pk)
    if claimed.status in {BillingEvent.Status.PROCESSED, BillingEvent.Status.IGNORED}:
        return claimed
    if claimed.status != BillingEvent.Status.PROCESSING:
        return claimed

    try:
        payload = claimed.payload if isinstance(claimed.payload, dict) else {}
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        if claimed.event_type.startswith("subscription."):
            sync_paddle_subscription(data, environment=environment)
        elif claimed.event_type.startswith("transaction."):
            sync_paddle_transaction(data, event_type=claimed.event_type, environment=environment)
        elif claimed.event_type.startswith("adjustment."):
            sync_paddle_adjustment(data, environment=environment)
        else:
            return finish_billing_event(claimed.pk, status=BillingEvent.Status.IGNORED)
    except (PaddleEventError, PaddleCheckoutUnavailable):
        return finish_billing_event(
            claimed.pk,
            status=BillingEvent.Status.IGNORED,
            last_error="InvalidPaddleResource",
        )
    except Exception as exc:
        finish_billing_event(claimed.pk, status=BillingEvent.Status.FAILED, last_error=type(exc).__name__)
        raise
    return finish_billing_event(claimed.pk, status=BillingEvent.Status.PROCESSED)


@transaction.atomic
def sync_paddle_subscription(data: Mapping[str, Any], *, environment: str) -> ProviderSubscription:
    subscription_id = _required_string(data, "id")
    provider_status = _required_string(data, "status").lower()
    status = _SUBSCRIPTION_STATUS_MAP.get(provider_status)
    if status is None:
        raise PaddleEventError("Unsupported Paddle subscription status.")

    existing = (
        ProviderSubscription.objects.select_for_update()
        .filter(provider=PaymentProvider.PADDLE, external_subscription_id=subscription_id)
        .first()
    )
    product = _resolve_product(data, environment=environment, existing=existing)
    user = _resolve_user(data, product=product, environment=environment, existing=existing)
    period = data.get("current_billing_period") if isinstance(data.get("current_billing_period"), dict) else {}
    scheduled_change = data.get("scheduled_change") if isinstance(data.get("scheduled_change"), dict) else {}
    metadata = dict(existing.metadata or {}) if existing is not None else {}
    metadata.update(
        {
            "paddle_customer_id": str(data.get("customer_id") or ""),
            "paddle_transaction_id": str(data.get("transaction_id") or ""),
            "paddle_environment": environment,
            "paddle_status": provider_status,
        }
    )
    subscription, _ = ProviderSubscription.objects.update_or_create(
        provider=PaymentProvider.PADDLE,
        external_subscription_id=subscription_id,
        defaults={
            "user": user,
            "product": product,
            "status": status,
            "current_period_start": _optional_datetime(period.get("starts_at")),
            "current_period_end": _optional_datetime(period.get("ends_at")),
            "cancel_at_period_end": scheduled_change.get("action") == "cancel",
            "metadata": metadata,
        },
    )
    project_provider_subscription(subscription)
    return subscription


@transaction.atomic
def sync_paddle_transaction(
    data: Mapping[str, Any],
    *,
    event_type: str,
    environment: str,
):
    transaction_id = _required_string(data, "id")
    subscription_id = str(data.get("subscription_id") or "").strip()
    if not subscription_id:
        raise PaddleEventError("A recurring Paddle transaction must include subscription_id.")

    subscription = ProviderSubscription.objects.filter(
        provider=PaymentProvider.PADDLE,
        external_subscription_id=subscription_id,
    ).first()
    if subscription is None:
        synthetic_subscription = dict(data)
        synthetic_subscription.update({"id": subscription_id, "status": "active"})
        subscription = sync_paddle_subscription(synthetic_subscription, environment=environment)

    provider_status = str(data.get("status") or "").lower()
    if event_type == "transaction.payment_failed":
        payment_status = "rejected"
    else:
        payment_status = _TRANSACTION_STATUS_MAP.get(provider_status)
    if payment_status is None:
        raise PaddleEventError("Unsupported Paddle transaction status.")

    details = data.get("details") if isinstance(data.get("details"), dict) else {}
    totals = details.get("totals") if isinstance(details.get("totals"), dict) else {}
    try:
        amount_minor = int(totals.get("total"))
    except (TypeError, ValueError) as exc:
        raise PaddleEventError("Paddle transaction total is invalid.") from exc
    currency = _required_string(data, "currency_code").upper()
    return sync_provider_payment(ProviderPaymentSnapshot(
        provider=PaymentProvider.PADDLE,
        external_payment_id=transaction_id,
        external_subscription_id=subscription.external_subscription_id,
        status=payment_status,
        amount_minor=amount_minor,
        currency=currency,
        approved_at=_optional_datetime(data.get("billed_at")) if payment_status == "approved" else None,
        metadata={
            "paddle_environment": environment,
            "paddle_status": provider_status,
            "paddle_invoice_number": str(data.get("invoice_number") or ""),
        },
    ))


@transaction.atomic
def sync_paddle_adjustment(data: Mapping[str, Any], *, environment: str) -> BillingPayment:
    adjustment_id = _required_string(data, "id")
    transaction_id = _required_string(data, "transaction_id")
    payment = (
        BillingPayment.objects.select_for_update()
        .filter(provider=PaymentProvider.PADDLE, external_payment_id=transaction_id)
        .first()
    )
    if payment is None:
        raise PaddleEventError("Paddle adjustment references an unknown transaction.")

    action = _required_string(data, "action").lower()
    adjustment_type = _required_string(data, "type").lower()
    adjustment_status = _required_string(data, "status").lower()
    metadata = dict(payment.metadata or {})
    adjustments = dict(metadata.get("paddle_adjustments") or {})
    totals = data.get("totals") if isinstance(data.get("totals"), dict) else {}
    adjustments[adjustment_id] = {
        "action": action,
        "type": adjustment_type,
        "status": adjustment_status,
        "total": str(totals.get("total") or ""),
        "currency": str(data.get("currency_code") or ""),
        "environment": environment,
    }
    metadata["paddle_adjustments"] = adjustments
    payment.metadata = metadata

    terminal_status = None
    if adjustment_status == "approved" and adjustment_type == "full":
        if action in {"refund", "credit"}:
            terminal_status = BillingPayment.Status.REFUNDED
        elif action == "chargeback":
            terminal_status = BillingPayment.Status.CHARGED_BACK
    if terminal_status is not None:
        payment.status = terminal_status
    payment.save(update_fields=["status", "metadata", "updated_at"])

    if terminal_status is not None and payment.subscription_id is not None:
        subscription = ProviderSubscription.objects.select_for_update().get(pk=payment.subscription_id)
        subscription.status = ProviderSubscription.Status.PAST_DUE
        subscription.save(update_fields=["status", "updated_at"])
        project_provider_subscription(subscription)
    return payment


def _resolve_product(
    data: Mapping[str, Any],
    *,
    environment: str,
    existing: ProviderSubscription | None,
) -> BillingProduct:
    price_id = _price_id(data)
    product = (
        BillingProduct.objects.select_related("offer", "account_plan")
        .filter(
            provider=PaymentProvider.PADDLE,
            environment=environment,
            external_price_id=price_id,
        )
        .first()
    )
    if product is None or (existing is None and not product.active):
        raise PaddleEventError("Paddle price is not mapped to a My Scoope offer.")
    return product


def _resolve_user(
    data: Mapping[str, Any],
    *,
    product: BillingProduct,
    environment: str,
    existing: ProviderSubscription | None,
):
    if existing is not None:
        return existing.user
    custom_data = data.get("custom_data") if isinstance(data.get("custom_data"), dict) else {}
    reference = str(custom_data.get("myscoope_checkout_reference") or "")
    checkout = read_paddle_checkout_reference(reference)
    if (
        checkout.get("product_id") != product.pk
        or checkout.get("offer_code") != product.offer.code
        or checkout.get("environment") != environment
    ):
        raise PaddleEventError("Paddle checkout reference does not match the catalog mapping.")
    user = get_user_model().objects.filter(pk=checkout.get("user_id")).first()
    if user is None:
        raise PaddleEventError("Paddle checkout references an unknown account.")
    return user


def _price_id(data: Mapping[str, Any]) -> str:
    items = data.get("items") if isinstance(data.get("items"), list) else []
    recurring_price_ids = []
    for item in items:
        if not isinstance(item, dict):
            continue
        price = item.get("price") if isinstance(item.get("price"), dict) else {}
        price_id = str(price.get("id") or item.get("price_id") or "").strip()
        if price_id:
            recurring_price_ids.append(price_id)
    if len(set(recurring_price_ids)) != 1:
        raise PaddleEventError("Paddle subscription must resolve to exactly one mapped price.")
    return recurring_price_ids[0]


def _required_string(data: Mapping[str, Any], key: str) -> str:
    value = str(data.get(key) or "").strip()
    if not value:
        raise PaddleEventError(f"Paddle field {key} is required.")
    return value


def _optional_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    parsed = parse_datetime(str(value))
    if parsed is None:
        raise PaddleEventError("Paddle datetime is invalid.")
    return parsed
