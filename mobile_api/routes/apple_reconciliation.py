"""Explicit, bounded reconciliation of this account's stored Apple subscriptions."""

import logging

from django_ratelimit.core import is_ratelimited
from ninja import Router

from billing.application.services.apple_app_store import AppleEvidenceError
from billing.infrastructure.providers.apple_app_store import InvalidAppleSignedData
from mobile_api.api_support import require_scope, success
from mobile_api.apple_billing import reconcile_apple_subscriptions_for_user
from mobile_api.auth import mobile_bearer
from mobile_api.billing_selector import subscription_payload
from mobile_api.entitlements_selector import entitlements_payload
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.billing_purchases import SubscriptionPurchaseEnvelope
from mobile_api.schemas import ErrorEnvelope
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router()
logger = logging.getLogger(__name__)


@router.post(
    "/subscriptions/apple/reconcile", operation_id="mobile_api_api_apple_reconcile", auth=mobile_bearer,
    response={200: SubscriptionPurchaseEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 409: ErrorEnvelope, 429: ErrorEnvelope, 503: ErrorEnvelope},
)
def apple_reconcile(request):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    if is_ratelimited(request, group="mobile_apple_reconcile", key="user", rate="10/m", increment=True):
        raise MobileAPIError("apple_reconciliation_rate_limited", "Wait before refreshing Apple subscription status again.", 429)
    try:
        reconcile_apple_subscriptions_for_user(request.auth.user)
    except (AppleEvidenceError, InvalidAppleSignedData) as exc:
        raise MobileAPIError("apple_transaction_mismatch", "Apple subscription evidence could not be reconciled.", 409) from exc
    except Exception as exc:
        logger.warning("Apple subscription reconciliation failed", extra={"error_class": type(exc).__name__})
        raise MobileAPIError("apple_billing_unavailable", "Apple reconciliation is temporarily unavailable.", 503) from exc
    return success({**subscription_payload(request.auth.user), "entitlements": entitlements_payload(request.auth.user)})
