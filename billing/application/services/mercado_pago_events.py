from __future__ import annotations

from billing.application.contracts import PaymentGateway
from billing.application.services.events import claim_billing_event, finish_billing_event
from billing.application.services.provider_sync import (
    UnknownBillingResource,
    sync_provider_payment,
    sync_provider_subscription,
)
from billing.models import BillingEvent

SUPPORTED_SUBSCRIPTION_TOPIC = "subscription_preapproval"
SUPPORTED_PAYMENT_TOPICS = {"payment", "subscription_authorized_payment"}


def process_mercado_pago_event(*, event: BillingEvent, gateway: PaymentGateway) -> BillingEvent:
    claimed = claim_billing_event(event.pk)
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
            return finish_billing_event(claimed.pk, status=BillingEvent.Status.IGNORED)
    except UnknownBillingResource:
        return finish_billing_event(
            claimed.pk,
            status=BillingEvent.Status.IGNORED,
            last_error="UnknownBillingResource",
        )
    except Exception as exc:
        finish_billing_event(claimed.pk, status=BillingEvent.Status.FAILED, last_error=type(exc).__name__)
        raise
    return finish_billing_event(claimed.pk, status=BillingEvent.Status.PROCESSED)
