from __future__ import annotations

from ninja import Router

from billing.application.services.apple_app_store import AppleEvidenceError, sync_apple_transaction
from billing.infrastructure.providers.apple_app_store import (
    AppleAppStoreConfigurationError,
    InvalidAppleSignedData,
)
from mobile_api.api_support import require_scope, success
from mobile_api.apple_billing import apple_purchases_enabled_for_user, verify_apple_transaction_for_user
from mobile_api.auth import mobile_bearer
from mobile_api.billing_selector import subscription_payload
from mobile_api.entitlements_selector import entitlements_payload
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.billing import (
    EntitlementsEnvelope,
    SubscriptionEnvelope,
)
from mobile_api.schema_domains.billing_purchases import SubscriptionPurchaseEnvelope
from mobile_api.schema_domains.store_billing import AppleTransactionInput
from mobile_api.schemas import ErrorEnvelope
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router()


@router.get(
    "/entitlements",
    operation_id="mobile_api_api_entitlements",
    auth=mobile_bearer,
    response={200: EntitlementsEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def entitlements(request):
    return success(entitlements_payload(request.auth.user))


@router.get(
    "/subscriptions",
    operation_id="mobile_api_api_subscriptions",
    auth=mobile_bearer,
    response={200: SubscriptionEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def subscriptions(request):
    return success(subscription_payload(request.auth.user))


@router.post(
    "/subscriptions/apple/transactions",
    operation_id="mobile_api_api_apple_transaction",
    auth=mobile_bearer,
    response={
        200: SubscriptionPurchaseEnvelope,
        403: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
        503: ErrorEnvelope,
    },
)
def apple_transaction(request, payload: AppleTransactionInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    if not apple_purchases_enabled_for_user(request.auth.user):
        raise MobileAPIError("apple_purchases_disabled", "Apple purchases are not enabled.", 403)
    try:
        evidence = verify_apple_transaction_for_user(payload.signed_transaction, user=request.auth.user)
        if payload.product_id and payload.product_id != evidence.product_id:
            raise AppleEvidenceError("The submitted product differs from the signed Apple product.")
        provider = sync_apple_transaction(evidence, expected_user=request.auth.user, source="mobile_storekit")
    except InvalidAppleSignedData as exc:
        raise MobileAPIError(
            code="apple_transaction_invalid",
            message="The StoreKit transaction could not be verified.",
            status_code=422,
        ) from exc
    except AppleEvidenceError as exc:
        raise MobileAPIError(
            code="apple_transaction_mismatch",
            message="The StoreKit transaction does not match this account or product.",
            status_code=409,
        ) from exc
    except AppleAppStoreConfigurationError as exc:
        raise MobileAPIError(
            code="apple_billing_unavailable",
            message="Apple purchase verification is temporarily unavailable.",
            status_code=503,
        ) from exc
    transaction_status = "superseded" if provider.metadata.get("apple_latest_transaction_id") != evidence.transaction_id else (
        "current" if provider.status == "authorized" else "inactive"
    )
    return success({**subscription_payload(request.auth.user), "entitlements": entitlements_payload(request.auth.user),
                    "transaction_status": transaction_status})
