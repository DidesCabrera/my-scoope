"""Fail-closed Apple transaction verification for the mobile API."""

import uuid
from dataclasses import replace

from appstoreserverlibrary.api_client import APIException
from django.conf import settings

from billing.application.services.apple_environment import (
    UnsupportedAppleEnvironment,
    apple_catalog_environment,
    user_has_apple_sandbox_access,
)
from billing.infrastructure.gateways import build_apple_app_store_gateway
from billing.infrastructure.providers.apple_app_store import AppleAppStoreConfigurationError, InvalidAppleSignedData
from billing.application.services.apple_app_store import (
    UnknownAppleAccountToken, get_or_create_apple_app_account_token, sync_apple_transaction,
)
from billing.models import AppleAppAccountToken, PaymentProvider, ProviderSubscription


def recover_unbound_sandbox_subscription(evidence, *, user):
    """Bind an unclaimed Sandbox chain using Apple's current signed status.

    This never transfers an existing chain or a token owned by another user.
    Production transactions retain the strict ownership rule.
    """
    if evidence.environment.lower() != "sandbox" or not user_has_apple_sandbox_access(user):
        raise UnknownAppleAccountToken("Sandbox recovery is unavailable.")
    if evidence.ownership_type.lower() in {"family_shared", "familyshared"}:
        raise UnknownAppleAccountToken("Family-shared purchases cannot be recovered.")
    if ProviderSubscription.objects.filter(
        provider=PaymentProvider.APPLE_APP_STORE,
        external_subscription_id=evidence.original_transaction_id,
    ).exists():
        raise UnknownAppleAccountToken("Apple subscription is already claimed.")
    if evidence.app_account_token:
        signed_owner = _token_owner(evidence.app_account_token)
        if signed_owner is not None and signed_owner != user.pk:
            raise UnknownAppleAccountToken("Signed Apple account token belongs to another account.")
    gateway = build_apple_app_store_gateway(environment="sandbox")
    try:
        current = _current_apple_subscription(gateway, evidence.original_transaction_id)
        if current.transaction.app_account_token:
            existing_owner = _token_owner(current.transaction.app_account_token)
            if existing_owner is not None and existing_owner != user.pk:
                raise UnknownAppleAccountToken("Apple account token belongs to another account.")
        token = get_or_create_apple_app_account_token(user)
        if _normalized_token(current.transaction.app_account_token) != token.token:
            gateway.set_app_account_token(evidence.original_transaction_id, str(token.token))
            # Apple's 200 response binds the current renewal to this token;
            # its signed status may still contain the previous token briefly.
            current = replace(current, transaction=replace(current.transaction, app_account_token=str(token.token)))
    except APIException as exc:
        raise AppleAppStoreConfigurationError("Apple Sandbox account recovery is temporarily unavailable.") from exc
    return sync_apple_transaction(
        current.transaction, expected_user=user, source="app_store_server_api_token_recovery",
    )


def _current_apple_subscription(gateway, original_transaction_id):
    for item in gateway.get_subscription_statuses(original_transaction_id):
        if item.transaction.original_transaction_id == original_transaction_id:
            _require_environment(item.transaction, verifier_environment="sandbox")
            return item
    raise AppleAppStoreConfigurationError("Apple did not return the current subscription status.")


def _normalized_token(value):
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError as exc:
        raise UnknownAppleAccountToken("Apple account token is invalid.") from exc


def _token_owner(value):
    token = AppleAppAccountToken.objects.filter(token=_normalized_token(value)).first()
    return token.user_id if token else None


def reconcile_apple_subscriptions_for_user(user) -> None:
    """At most one status request per stored Apple environment, bound to this account."""
    rows = ProviderSubscription.objects.select_related("product").filter(
        user=user, provider=PaymentProvider.APPLE_APP_STORE,
    ).order_by("-updated_at")
    environments = set()
    for row in rows:
        environment = "sandbox" if row.product.environment == "sandbox" else "production"
        if environment in environments:
            continue
        environments.add(environment)
        gateway = build_apple_app_store_gateway(environment=environment)
        for item in gateway.get_subscription_statuses(row.external_subscription_id):
            _require_environment(item.transaction, verifier_environment=environment)
            sync_apple_transaction(item.transaction, expected_user=user, source="app_store_server_api")


def verify_apple_transaction_for_user(signed_transaction: str, *, user):
    """Verify only environments this account may purchase in; never bypass the live kill switch."""

    sandbox_allowed = (
        settings.BILLING_APPLE_ENVIRONMENT == "production"
        and settings.BILLING_APPLE_SANDBOX_PURCHASES_ENABLED
        and user_has_apple_sandbox_access(user)
    )
    if not settings.BILLING_APPLE_PURCHASES_ENABLED:
        if not sandbox_allowed:
            raise InvalidAppleSignedData("Apple purchases are disabled for this account.")
        evidence = build_apple_app_store_gateway(environment="sandbox").verify_transaction(signed_transaction)
        _require_environment(evidence, verifier_environment="sandbox")
        return evidence

    try:
        evidence = build_apple_app_store_gateway().verify_transaction(signed_transaction)
        _require_environment(evidence, verifier_environment=settings.BILLING_APPLE_ENVIRONMENT)
        return evidence
    except InvalidAppleSignedData:
        if not sandbox_allowed:
            raise
    evidence = build_apple_app_store_gateway(environment="sandbox").verify_transaction(signed_transaction)
    _require_environment(evidence, verifier_environment="sandbox")
    return evidence


def apple_purchase_environment_for_user(user) -> str | None:
    """Select the Apple catalog a user may purchase from, preferring authorized sandbox access."""

    if (
        settings.BILLING_APPLE_ENVIRONMENT == "production"
        and settings.BILLING_APPLE_SANDBOX_PURCHASES_ENABLED
        and user_has_apple_sandbox_access(user)
    ):
        return "sandbox"
    if not settings.BILLING_APPLE_PURCHASES_ENABLED:
        return None
    try:
        apple_catalog_environment(settings.BILLING_APPLE_ENVIRONMENT)
    except UnsupportedAppleEnvironment:
        return None
    return settings.BILLING_APPLE_ENVIRONMENT


def apple_purchases_enabled_for_user(user) -> bool:
    return apple_purchase_environment_for_user(user) is not None


def _require_environment(evidence, *, verifier_environment: str) -> None:
    try:
        if apple_catalog_environment(evidence.environment) != apple_catalog_environment(verifier_environment):
            raise InvalidAppleSignedData("The StoreKit transaction environment does not match the verifier.")
    except UnsupportedAppleEnvironment as exc:
        raise InvalidAppleSignedData("The StoreKit transaction environment is invalid.") from exc
