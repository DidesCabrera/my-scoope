"""Fail-closed Apple transaction verification for the mobile API."""

from django.conf import settings

from billing.application.services.apple_app_store import (
    UnsupportedAppleEnvironment,
    apple_catalog_environment,
    user_has_apple_sandbox_access,
)
from billing.infrastructure.gateways import build_apple_app_store_gateway
from billing.infrastructure.providers.apple_app_store import InvalidAppleSignedData


def verify_apple_transaction_for_user(signed_transaction: str, *, user):
    """Verify against the configured environment, with an authorized production-only sandbox fallback."""

    try:
        evidence = build_apple_app_store_gateway().verify_transaction(signed_transaction)
        _require_environment(evidence, verifier_environment=settings.BILLING_APPLE_ENVIRONMENT)
        return evidence
    except InvalidAppleSignedData:
        if not (
            settings.BILLING_APPLE_ENVIRONMENT == "production"
            and settings.BILLING_APPLE_SANDBOX_PURCHASES_ENABLED
            and user_has_apple_sandbox_access(user)
        ):
            raise
    evidence = build_apple_app_store_gateway(environment="sandbox").verify_transaction(signed_transaction)
    _require_environment(evidence, verifier_environment="sandbox")
    return evidence


def _require_environment(evidence, *, verifier_environment: str) -> None:
    try:
        if apple_catalog_environment(evidence.environment) != apple_catalog_environment(verifier_environment):
            raise InvalidAppleSignedData("The StoreKit transaction environment does not match the verifier.")
    except UnsupportedAppleEnvironment as exc:
        raise InvalidAppleSignedData("The StoreKit transaction environment is invalid.") from exc
