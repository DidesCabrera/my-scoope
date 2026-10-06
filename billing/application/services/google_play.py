from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from billing.application.contracts import GooglePlaySubscriptionEvidence
from billing.application.services.events import claim_billing_event, finish_billing_event
from billing.application.services.google_play_validation import (
    GooglePlayEvidenceError,
    get_or_create_google_play_account_token,
    google_play_account_id,
    google_play_environment,
)
from billing.application.services.projections import project_provider_subscription
from billing.models import (
    BillingEvent,
    BillingProduct,
    CreditPackPurchase,
    GooglePlayAccountToken,
    PaymentProvider,
    ProviderSubscription,
)


def google_play_user_for_account_id(value: str):
    token = GooglePlayAccountToken.objects.select_related("user").filter(token=str(value or "")).first()
    if token is None:
        raise GooglePlayEvidenceError("The Google Play account token is unknown.")
    return token.user


@transaction.atomic
def sync_google_play_subscription(
    evidence: GooglePlaySubscriptionEvidence,
    *,
    expected_user,
    expected_environment: str | None = None,
):
    account_token = get_or_create_google_play_account_token(expected_user)
    if evidence.obfuscated_account_id != account_token.token:
        raise GooglePlayEvidenceError("The Google Play purchase belongs to another account.")
    environment = google_play_environment(evidence.environment)
    if expected_environment is not None and environment != google_play_environment(expected_environment):
        raise GooglePlayEvidenceError("The Google Play purchase belongs to another environment.")
    product = BillingProduct.objects.filter(
        provider=PaymentProvider.GOOGLE_PLAY,
        environment=environment,
        external_product_id=evidence.product_id,
        external_price_id=evidence.base_plan_id,
        active=True,
    ).first()
    if product is None:
        raise GooglePlayEvidenceError("The Google Play product is not mapped to a My Scoope plan.")
    status = _status(evidence.status, expiry_time=evidence.expiry_time)
    existing = ProviderSubscription.objects.select_for_update().filter(
        provider=PaymentProvider.GOOGLE_PLAY,
        external_subscription_id=evidence.purchase_token,
    ).first()
    if existing is not None and existing.user_id != expected_user.pk:
        raise GooglePlayEvidenceError("The Google Play purchase token is already assigned.")
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
            "metadata": {
                "google_play": dict(evidence.metadata or {}),
                "google_play_environment": environment,
                "google_play_acknowledged": evidence.acknowledged,
            },
        },
    )
    project_provider_subscription(subscription)
    return subscription


def process_google_play_notification(*, event: BillingEvent, notification, gateway, expected_environment: str):
    """Refresh provider state for one authenticated RTDN without trusting its status."""

    claimed = claim_billing_event(event.pk)
    if claimed.status in {BillingEvent.Status.PROCESSED, BillingEvent.Status.IGNORED}:
        return claimed
    if claimed.status != BillingEvent.Status.PROCESSING:
        return claimed
    try:
        if notification.kind == "test":
            return finish_billing_event(claimed.pk, status=BillingEvent.Status.PROCESSED)
        if notification.kind == "subscription":
            evidence = gateway.verify_subscription(notification.purchase_token)
            if notification.product_id and evidence.product_id != notification.product_id:
                raise GooglePlayEvidenceError("Google Play RTDN subscription product does not match.")
            subscription = ProviderSubscription.objects.filter(
                provider=PaymentProvider.GOOGLE_PLAY,
                external_subscription_id=notification.purchase_token,
            ).select_related("user").first()
            owner = subscription.user if subscription is not None else google_play_user_for_account_id(
                evidence.obfuscated_account_id
            )
            sync_google_play_subscription(
                evidence,
                expected_user=owner,
                expected_environment=expected_environment,
            )
        else:
            _process_google_play_product_notification(
                notification=notification,
                gateway=gateway,
                expected_environment=expected_environment,
            )
    except Exception as exc:
        finish_billing_event(claimed.pk, status=BillingEvent.Status.FAILED, last_error=type(exc).__name__)
        raise
    return finish_billing_event(claimed.pk, status=BillingEvent.Status.PROCESSED)


def _process_google_play_product_notification(*, notification, gateway, expected_environment: str) -> None:
    from billing.application.services.credit_packs import (
        refund_credit_pack_purchase,
        settle_google_play_credit_pack,
        stored_credit_pack_purchase_id,
    )

    evidence = gateway.verify_product(notification.purchase_token)
    if notification.product_id and evidence.product_id != notification.product_id:
        raise GooglePlayEvidenceError("Google Play RTDN product does not match.")
    environment = google_play_environment(evidence.environment)
    if environment != google_play_environment(expected_environment):
        raise GooglePlayEvidenceError("Google Play RTDN belongs to another environment.")
    purchase = CreditPackPurchase.objects.filter(
        provider=PaymentProvider.GOOGLE_PLAY,
        external_purchase_id=stored_credit_pack_purchase_id(
            provider=PaymentProvider.GOOGLE_PLAY,
            purchase_id=notification.purchase_token,
        ),
    ).select_related("user").first()
    if evidence.status == "PURCHASED":
        owner = purchase.user if purchase is not None else google_play_user_for_account_id(
            evidence.obfuscated_account_id
        )
        settle_google_play_credit_pack(
            user=owner,
            evidence=evidence,
            expected_environment=expected_environment,
        )
    elif evidence.status == "CANCELLED" and purchase is not None:
        refund_credit_pack_purchase(
            provider=PaymentProvider.GOOGLE_PLAY,
            external_purchase_id=notification.purchase_token,
        )
    elif evidence.status not in {"CANCELLED", "PENDING"}:
        raise GooglePlayEvidenceError("Google Play returned an unsupported product state.")


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
