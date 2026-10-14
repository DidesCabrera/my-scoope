"""Fail-closed Apple transaction verification for the mobile API."""

from django.conf import settings

from billing.application.services.apple_environment import (
    UnsupportedAppleEnvironment,
    apple_catalog_environment,
    user_has_apple_sandbox_access,
)
from billing.infrastructure.gateways import build_apple_app_store_gateway
from billing.infrastructure.providers.apple_app_store import InvalidAppleSignedData
from billing.application.services.apple_app_store import sync_apple_transaction
from billing.models import PaymentProvider, ProviderSubscription


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
