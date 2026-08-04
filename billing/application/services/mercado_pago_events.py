from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from billing.application.contracts import PaymentGateway
from billing.application.services.provider_sync import (
    UnknownBillingResource,
    sync_provider_payment,
    sync_provider_subscription,
)
from billing.models import BillingEvent

SUPPORTED_SUBSCRIPTION_TOPIC = "subscription_preapproval"
SUPPORTED_PAYMENT_TOPICS = {"payment", "subscription_authorized_payment"}


def process_mercado_pago_event(*, event: BillingEvent, gateway: PaymentGateway) -> BillingEvent:
    claimed = _claim_event(event.pk)
    if claimed.status in {BillingEvent.Status.PROCESSED, BillingEvent.Status.IGNORED}:
        return claimed
    if claimed.status != BillingEvent.Status.PROCESSING:
        return claimed

    try:
        if claimed.event_type == SUPPORTED_SUBSCRIPTION_TOPIC:
            snapshot = gateway.get_subscription(claimed.resource_id)
            sync_provider_subscription(snapshot)
        elif claimed.event_type == "payment":
            snapshot = gateway.get_payment(claimed.resource_id)
            sync_provider_payment(snapshot)
        elif claimed.event_type == "subscription_authorized_payment":
            snapshot = gateway.get_authorized_payment(claimed.resource_id)
            sync_provider_payment(snapshot)
        else:
            return _finish_event(claimed.pk, status=BillingEvent.Status.IGNORED)
    except UnknownBillingResource:
        return _finish_event(
            claimed.pk,
            status=BillingEvent.Status.IGNORED,
            last_error="UnknownBillingResource",
        )
    except Exception as exc:
        _finish_event(claimed.pk, status=BillingEvent.Status.FAILED, last_error=type(exc).__name__)
        raise
    return _finish_event(claimed.pk, status=BillingEvent.Status.PROCESSED)


@transaction.atomic
def _claim_event(event_id: int) -> BillingEvent:
    event = BillingEvent.objects.select_for_update().get(pk=event_id)
    if event.status in {BillingEvent.Status.PROCESSED, BillingEvent.Status.IGNORED, BillingEvent.Status.PROCESSING}:
        return event
    event.status = BillingEvent.Status.PROCESSING
    event.attempts += 1
    event.last_error = ""
    event.save(update_fields=["status", "attempts", "last_error"])
    return event


@transaction.atomic
def _finish_event(event_id: int, *, status: str, last_error: str = "") -> BillingEvent:
    event = BillingEvent.objects.select_for_update().get(pk=event_id)
    event.status = status
    event.last_error = last_error[:500]
    event.processed_at = timezone.now() if status in {BillingEvent.Status.PROCESSED, BillingEvent.Status.IGNORED} else None
    event.save(update_fields=["status", "last_error", "processed_at"])
    return event
