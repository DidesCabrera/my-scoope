"""Verified Apple subscription evidence and entitlement projection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from django.db import transaction
from django.utils import timezone

from billing.application.contracts import AppleNotificationEvidence, AppleTransactionEvidence
from billing.application.services.events import claim_billing_event, finish_billing_event
from billing.application.services.projections import project_provider_subscription
from billing.models import (
    AppleAppAccountToken,
    BillingEvent,
    BillingProduct,
    PaymentProvider,
    ProviderSubscription,
)


class AppleEvidenceError(ValueError):
    pass


class UnknownAppleAccountToken(AppleEvidenceError):
    pass


class UnsupportedAppleProduct(AppleEvidenceError):
    pass


class UnsupportedAppleOwnership(AppleEvidenceError):
    pass


_STATUS_MAP = {
    "active": ProviderSubscription.Status.AUTHORIZED,
    "grace_period": ProviderSubscription.Status.AUTHORIZED,
    "billing_retry": ProviderSubscription.Status.PAST_DUE,
    "expired": ProviderSubscription.Status.EXPIRED,
    "revoked": ProviderSubscription.Status.CANCELED,
}


def get_or_create_apple_app_account_token(user) -> AppleAppAccountToken:
    token, _ = AppleAppAccountToken.objects.get_or_create(user=user)
    return token


@transaction.atomic
def sync_apple_transaction(
    evidence: AppleTransactionEvidence,
    *,
    expected_user=None,
    source: str,
) -> ProviderSubscription:
    """Bind verified StoreKit evidence to an account and project entitlements."""

    original_id = evidence.original_transaction_id.strip()
    transaction_id = evidence.transaction_id.strip()
    product_id = evidence.product_id.strip()
    if not original_id or not transaction_id or not product_id:
        raise AppleEvidenceError("Apple transaction identity is incomplete.")
    if evidence.ownership_type.lower() in {"family_shared", "familyshared"}:
        raise UnsupportedAppleOwnership("Family-shared purchases are not supported in CML06.")

    existing = (
        ProviderSubscription.objects.select_for_update()
        .filter(provider=PaymentProvider.APPLE_APP_STORE, external_subscription_id=original_id)
        .first()
    )
    owner = _resolve_owner(evidence.app_account_token, existing=existing)
    if expected_user is not None and owner.pk != expected_user.pk:
        raise UnknownAppleAccountToken("The Apple transaction belongs to another My Scoope account.")

    product = (
        BillingProduct.objects.select_related("account_plan")
        .filter(provider=PaymentProvider.APPLE_APP_STORE, external_product_id=product_id)
        .first()
    )
    if product is None or (existing is None and not product.active):
        raise UnsupportedAppleProduct("The Apple product is not mapped to a My Scoope plan.")

    status = _provider_status(evidence)
    metadata = dict(existing.metadata or {}) if existing is not None else {}
    metadata.update(
        {
            **dict(evidence.metadata or {}),
            "apple_latest_transaction_id": transaction_id,
            "apple_environment": evidence.environment,
            "apple_ownership_type": evidence.ownership_type,
            "apple_evidence_source": source,
            "apple_signed_date": _iso_datetime(evidence.signed_date),
            "apple_status": evidence.status,
        }
    )
    defaults = {
        "user": owner,
        "product": product,
        "status": status,
        "current_period_start": _as_datetime(evidence.purchase_date),
        "current_period_end": _as_datetime(evidence.expires_date),
        "cancel_at_period_end": status in {
            ProviderSubscription.Status.CANCELED,
            ProviderSubscription.Status.EXPIRED,
        },
        "metadata": metadata,
    }
    subscription, _ = ProviderSubscription.objects.update_or_create(
        provider=PaymentProvider.APPLE_APP_STORE,
        external_subscription_id=original_id,
        defaults=defaults,
    )
    project_provider_subscription(subscription)
    return subscription


def process_apple_notification(*, event: BillingEvent, notification: AppleNotificationEvidence) -> BillingEvent:
    claimed = claim_billing_event(event.pk)
    if claimed.status in {BillingEvent.Status.PROCESSED, BillingEvent.Status.IGNORED}:
        return claimed
    if claimed.status != BillingEvent.Status.PROCESSING:
        return claimed
    try:
        if notification.transaction is None:
            return finish_billing_event(claimed.pk, status=BillingEvent.Status.IGNORED)
        sync_apple_transaction(notification.transaction, source="app_store_notification_v2")
    except AppleEvidenceError as exc:
        return finish_billing_event(
            claimed.pk,
            status=BillingEvent.Status.IGNORED,
            last_error=type(exc).__name__,
        )
    except Exception as exc:
        finish_billing_event(claimed.pk, status=BillingEvent.Status.FAILED, last_error=type(exc).__name__)
        raise
    return finish_billing_event(claimed.pk, status=BillingEvent.Status.PROCESSED)


def _resolve_owner(token_value: str, *, existing: ProviderSubscription | None):
    if token_value:
        try:
            normalized = uuid.UUID(str(token_value))
        except ValueError as exc:
            raise UnknownAppleAccountToken("Apple appAccountToken is invalid.") from exc
        token = AppleAppAccountToken.objects.select_for_update().filter(token=normalized).select_related("user").first()
        if token is None:
            raise UnknownAppleAccountToken("Apple appAccountToken is unknown.")
        if existing is not None and existing.user_id != token.user_id:
            raise UnknownAppleAccountToken("Apple transaction ownership changed unexpectedly.")
        return token.user
    if existing is not None:
        return existing.user
    raise UnknownAppleAccountToken("Apple appAccountToken is required for a new subscription.")


def _provider_status(evidence: AppleTransactionEvidence) -> str:
    if evidence.revocation_date is not None:
        return ProviderSubscription.Status.CANCELED
    status = _STATUS_MAP.get(evidence.status.lower())
    if status is None:
        raise AppleEvidenceError("Apple subscription status is unsupported.")
    expires_at = _as_datetime(evidence.expires_date)
    if status == ProviderSubscription.Status.AUTHORIZED and expires_at is not None and expires_at <= timezone.now():
        return ProviderSubscription.Status.EXPIRED
    return status


def _as_datetime(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value) / 1000, tz=UTC)
    raise AppleEvidenceError("Apple timestamp has an unsupported representation.")


def _iso_datetime(value) -> str:
    converted = _as_datetime(value)
    return converted.isoformat() if converted is not None else ""
