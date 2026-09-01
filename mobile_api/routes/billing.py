from __future__ import annotations

from django.conf import settings
from ninja import Router

from billing.application.services.apple_app_store import AppleEvidenceError, sync_apple_transaction
from billing.infrastructure.gateways import build_apple_app_store_gateway
from billing.infrastructure.providers.apple_app_store import (
    AppleAppStoreConfigurationError,
    InvalidAppleSignedData,
)
from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.billing import (
    AppleTransactionInput,
    EntitlementsEnvelope,
    SubscriptionEnvelope,
)
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors import entitlements_payload, subscription_payload
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
    return success(
        subscription_payload(
            request.auth.user,
            purchases_enabled=settings.BILLING_APPLE_PURCHASES_ENABLED,
        )
    )


@router.post(
    "/subscriptions/apple/transactions",
    operation_id="mobile_api_api_apple_transaction",
    auth=mobile_bearer,
    response={
        200: SubscriptionEnvelope,
        403: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
        503: ErrorEnvelope,
    },
)
def apple_transaction(request, payload: AppleTransactionInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    if not settings.BILLING_APPLE_PURCHASES_ENABLED:
        raise MobileAPIError(
            code="apple_purchases_disabled",
            message="Apple purchases are not enabled.",
            status_code=403,
        )
    try:
        evidence = build_apple_app_store_gateway().verify_transaction(payload.signed_transaction)
        sync_apple_transaction(evidence, expected_user=request.auth.user, source="mobile_storekit")
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
    return success(subscription_payload(request.auth.user, purchases_enabled=True))
