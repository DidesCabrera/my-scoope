"""Verified Apple subscription evidence and entitlement projection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from billing.application.contracts import AppleNotificationEvidence, AppleTransactionEvidence
from billing.application.services.apple_environment import (
    AppleEvidenceError,
    UnauthorizedAppleSandboxAccess,
    UnsupportedAppleEnvironment,
    apple_catalog_environment,
    require_apple_sandbox_access_in_production,
    user_has_apple_sandbox_access,
)
from billing.application.services.events import claim_billing_event, finish_billing_event
from billing.application.services.projections import project_provider_subscription
from billing.models import (
    AppleAppAccountToken,
    BillingEvent,
    BillingProduct,
    PaymentProvider,
    ProviderCreditPack,
    ProviderSubscription,
)


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
    catalog_environment = apple_catalog_environment(evidence.environment)

    existing = (
        ProviderSubscription.objects.select_related("product")
        .filter(provider=PaymentProvider.APPLE_APP_STORE, external_subscription_id=original_id)
        .first()
    )
    owner = _resolve_owner(evidence.app_account_token, existing=existing)
    if expected_user is not None and owner.pk != expected_user.pk:
        raise UnknownAppleAccountToken("The Apple transaction belongs to another My Scoope account.")
    # Serialize every Apple chain for this account before taking evidence locks.
    get_user_model().objects.select_for_update().get(pk=owner.pk)
    existing = ProviderSubscription.objects.select_for_update(of=("self",)).select_related("product").filter(
        provider=PaymentProvider.APPLE_APP_STORE, external_subscription_id=original_id,
    ).first()
    if existing is not None and existing.user_id != owner.pk:
        raise UnknownAppleAccountToken("Apple transaction ownership changed unexpectedly.")

    product = (
        BillingProduct.objects.select_related("account_plan")
        .filter(
            provider=PaymentProvider.APPLE_APP_STORE,
            environment=catalog_environment,
            external_product_id=product_id,
        )
        .first()
    )
    if product is None or (existing is None and not product.active):
        raise UnsupportedAppleProduct("The Apple product is not mapped to a My Scoope plan.")

    status = _provider_status(evidence)
    if existing is not None and existing.product.environment != catalog_environment:
        raise UnsupportedAppleEnvironment("Apple subscription environment changed unexpectedly.")
    if existing is not None and _is_stale_evidence(evidence, existing, source=source):
        return _current_subscription(existing)
    if status not in {ProviderSubscription.Status.CANCELED, ProviderSubscription.Status.EXPIRED}:
        require_apple_sandbox_access_in_production(owner, catalog_environment=catalog_environment)
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
        "current_period_end": _access_deadline(evidence),
        "cancel_at_period_end": metadata.get("apple_auto_renew_enabled") is False or status in {
            ProviderSubscription.Status.CANCELED,
            ProviderSubscription.Status.EXPIRED,
        },
        "metadata": metadata,
    }
    subscription, created = ProviderSubscription.objects.get_or_create(
        provider=PaymentProvider.APPLE_APP_STORE,
        external_subscription_id=original_id,
        defaults=defaults,
    )
    if not created:
        subscription = ProviderSubscription.objects.select_for_update().get(pk=subscription.pk)
        if subscription.user_id != owner.pk:
            raise UnknownAppleAccountToken("Apple transaction ownership changed unexpectedly.")
        if subscription.product.environment != catalog_environment:
            raise UnsupportedAppleEnvironment("Apple subscription environment changed unexpectedly.")
        if _is_stale_evidence(evidence, subscription, source=source):
            return _current_subscription(subscription)
        defaults["metadata"] = {**dict(subscription.metadata or {}), **defaults["metadata"]}
        for field, value in defaults.items():
            setattr(subscription, field, value)
        subscription.save()
    project_provider_subscription(subscription)
    return subscription


def _current_subscription(subscription):
    # Ignoring a stale receipt must not preserve an authorization whose known
    # deadline has since passed. Recompute any remaining provider entitlement.
    if subscription.status == ProviderSubscription.Status.AUTHORIZED and subscription.current_period_end and subscription.current_period_end <= timezone.now():
        project_provider_subscription(subscription)
        subscription.refresh_from_db()
    return subscription


def process_apple_notification(*, event: BillingEvent, notification: AppleNotificationEvidence) -> BillingEvent:
    try:
        return _process_apple_notification_atomic(event=event, notification=notification)
    except AppleEvidenceError as exc:
        return finish_billing_event(event.pk, status=BillingEvent.Status.IGNORED, last_error=type(exc).__name__)
    except Exception as exc:
        finish_billing_event(event.pk, status=BillingEvent.Status.FAILED, last_error=type(exc).__name__)
        raise


@transaction.atomic
def _process_apple_notification_atomic(*, event: BillingEvent, notification: AppleNotificationEvidence) -> BillingEvent:
    # The event lock stays held through settlement and its final status. A
    # concurrent duplicate cannot claim or settle the same notification twice.
    BillingEvent.objects.select_for_update().get(pk=event.pk)
    claimed = claim_billing_event(event.pk)
    if claimed.status in {BillingEvent.Status.PROCESSED, BillingEvent.Status.IGNORED}:
        return claimed
    if claimed.status != BillingEvent.Status.PROCESSING:
        return claimed
    if notification.transaction is None:
        return finish_billing_event(claimed.pk, status=BillingEvent.Status.IGNORED)
    evidence = notification.transaction
    catalog_environment = apple_catalog_environment(evidence.environment or notification.environment)
    is_pack = ProviderCreditPack.objects.filter(
        provider=PaymentProvider.APPLE_APP_STORE,
        environment=catalog_environment,
        external_product_id=evidence.product_id,
    ).exists()
    if is_pack:
        from billing.application.services.credit_packs import (
            refund_apple_credit_pack,
            settle_apple_credit_pack,
        )
        if notification.notification_type == "ONE_TIME_CHARGE":
            owner = _resolve_owner(evidence.app_account_token, existing=None)
            settle_apple_credit_pack(user=owner, evidence=evidence)
        elif notification.notification_type == "REFUND":
            owner = _resolve_owner(evidence.app_account_token, existing=None)
            refund_apple_credit_pack(user=owner, evidence=evidence)
        else:
            return finish_billing_event(claimed.pk, status=BillingEvent.Status.IGNORED)
    else:
        sync_apple_transaction(evidence, source="app_store_notification_v2")
    return finish_billing_event(claimed.pk, status=BillingEvent.Status.PROCESSED)


def _resolve_owner(token_value: str, *, existing: ProviderSubscription | None):
    if token_value:
        try:
            normalized = uuid.UUID(str(token_value))
        except ValueError as exc:
            raise UnknownAppleAccountToken("Apple appAccountToken is invalid.") from exc
        token = AppleAppAccountToken.objects.filter(token=normalized).select_related("user").first()
        if token is None:
            raise UnknownAppleAccountToken("Apple appAccountToken is unknown.")
        if existing is not None and existing.user_id != token.user_id:
            raise UnknownAppleAccountToken("Apple transaction ownership changed unexpectedly.")
        return token.user
    if existing is not None:
        return existing.user
    raise UnknownAppleAccountToken("Apple appAccountToken is required for a new subscription.")


def _provider_status(evidence: AppleTransactionEvidence) -> str:
    if evidence.expires_date is None:
        raise AppleEvidenceError("An Apple subscription requires an expiration date.")
    if evidence.revocation_date is not None:
        return ProviderSubscription.Status.CANCELED
    status = _STATUS_MAP.get(evidence.status.lower())
    if status is None:
        raise AppleEvidenceError("Apple subscription status is unsupported.")
    if (evidence.metadata or {}).get("apple_is_upgraded"):
        return ProviderSubscription.Status.EXPIRED
    expires_at = _access_deadline(evidence)
    if status == ProviderSubscription.Status.AUTHORIZED and expires_at is not None and expires_at <= timezone.now():
        return ProviderSubscription.Status.EXPIRED
    return status


def _access_deadline(evidence: AppleTransactionEvidence) -> datetime | None:
    if evidence.status.lower() == "grace_period":
        deadline = (evidence.metadata or {}).get("apple_grace_period_expires_date")
        if deadline is None:
            raise AppleEvidenceError("Apple grace period requires verified renewal evidence.")
        return _as_datetime(deadline)
    return _as_datetime(evidence.expires_date)


def _is_stale_evidence(evidence, existing, *, source: str) -> bool:
    current_id = (existing.metadata or {}).get("apple_latest_transaction_id")
    incoming_start = _as_datetime(evidence.purchase_date)
    if current_id != evidence.transaction_id and incoming_start and existing.current_period_start:
        if incoming_start < existing.current_period_start:
            return True
    elif current_id == evidence.transaction_id:
        # StoreKit's transaction alone cannot undo a later lifecycle decision
        # (refund, grace/retry, or renewal preference) about this transaction.
        if source == "mobile_storekit" and (existing.metadata or {}).get("apple_evidence_source") != "mobile_storekit":
            return True
        signed = _as_datetime(evidence.signed_date)
        stored = (existing.metadata or {}).get("apple_signed_date")
        if signed and stored and signed < datetime.fromisoformat(stored):
            return True
        if existing.status == ProviderSubscription.Status.CANCELED and not evidence.revocation_date:
            if not signed or not stored or signed <= datetime.fromisoformat(stored):
                return True
    return False


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
