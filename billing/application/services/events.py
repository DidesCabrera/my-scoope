"""Idempotent billing-event inbox use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from django.db import transaction

from billing.models import BillingEvent


class UnverifiedBillingEvent(ValueError):
    pass


@dataclass(frozen=True)
class BillingEventReceipt:
    event: BillingEvent
    created: bool


@transaction.atomic
def receive_verified_billing_event(
    *,
    provider: str,
    external_event_id: str,
    event_type: str,
    resource_id: str = "",
    payload: Mapping[str, Any] | None = None,
    signature_verified: bool,
) -> BillingEventReceipt:
    """Persist one authenticated provider event without replaying duplicates."""

    if not signature_verified:
        raise UnverifiedBillingEvent("Billing events must be authenticated before persistence.")
    if not external_event_id.strip():
        raise ValueError("external_event_id is required.")

    event, created = BillingEvent.objects.get_or_create(
        provider=provider,
        external_event_id=external_event_id.strip(),
        defaults={
            "event_type": event_type.strip(),
            "resource_id": resource_id.strip(),
            "signature_verified": True,
            "payload": dict(payload or {}),
        },
    )
    return BillingEventReceipt(event=event, created=created)
