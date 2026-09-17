from __future__ import annotations

import hashlib
from datetime import datetime

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from billing.application.contracts import GooglePlaySubscriptionEvidence
from billing.application.services.projections import project_provider_subscription
from billing.models import BillingProduct, PaymentProvider, ProviderSubscription


class GooglePlayEvidenceError(ValueError):
    pass


def google_play_account_id(user) -> str:
    return hashlib.sha256(f"myscoope:{user.pk}".encode()).hexdigest()


@transaction.atomic
def sync_google_play_subscription(evidence: GooglePlaySubscriptionEvidence, *, expected_user):
    if evidence.obfuscated_account_id != google_play_account_id(expected_user):
        raise GooglePlayEvidenceError("The Google Play purchase belongs to another account.")
    product = BillingProduct.objects.filter(
        provider=PaymentProvider.GOOGLE_PLAY,
        external_product_id=evidence.product_id,
        external_price_id=evidence.base_plan_id,
        active=True,
    ).first()
    if product is None:
        raise GooglePlayEvidenceError("The Google Play product is not mapped to a My Scoope plan.")
    status = _status(evidence.status, expiry_time=evidence.expiry_time)
    subscription, _ = ProviderSubscription.objects.update_or_create(
        provider=PaymentProvider.GOOGLE_PLAY,
        external_subscription_id=evidence.purchase_token,
        defaults={
            "user": expected_user,
            "product": product,
            "status": status,
            "current_period_start": _datetime(evidence.start_time),
            "current_period_end": _datetime(evidence.expiry_time),
            "cancel_at_period_end": status == ProviderSubscription.Status.CANCELED or not evidence.auto_renewing,
            "metadata": {"google_play": dict(evidence.metadata or {})},
        },
    )
    if subscription.user_id != expected_user.pk:
        raise GooglePlayEvidenceError("The Google Play purchase token is already assigned.")
    project_provider_subscription(subscription)
    return subscription


def _status(value: str, *, expiry_time=None) -> str:
    mapping = {
        "SUBSCRIPTION_STATE_ACTIVE": ProviderSubscription.Status.AUTHORIZED,
        "SUBSCRIPTION_STATE_IN_GRACE_PERIOD": ProviderSubscription.Status.AUTHORIZED,
        "SUBSCRIPTION_STATE_PENDING": ProviderSubscription.Status.PENDING,
        "SUBSCRIPTION_STATE_PAUSED": ProviderSubscription.Status.PAUSED,
        "SUBSCRIPTION_STATE_ON_HOLD": ProviderSubscription.Status.PAST_DUE,
        "SUBSCRIPTION_STATE_EXPIRED": ProviderSubscription.Status.EXPIRED,
    }
    if value == "SUBSCRIPTION_STATE_CANCELED":
        expires_at = _datetime(expiry_time)
        return (
            ProviderSubscription.Status.AUTHORIZED
            if expires_at is not None and expires_at > timezone.now()
            else ProviderSubscription.Status.EXPIRED
        )
    if value not in mapping:
        raise GooglePlayEvidenceError("Google Play returned an unsupported subscription state.")
    return mapping[value]


def _datetime(value) -> datetime | None:
    return parse_datetime(str(value)) if value else None
