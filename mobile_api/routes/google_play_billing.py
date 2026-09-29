import logging

from django.conf import settings
from ninja import Field, Router, Schema

from billing.application.services.credit_packs import CreditPackUnavailable, settle_google_play_credit_pack
from billing.application.services.google_play import GooglePlayEvidenceError, sync_google_play_subscription
from billing.infrastructure.gateways import build_google_play_gateway
from billing.infrastructure.providers.google_play import GooglePlayConfigurationError, InvalidGooglePlayPurchase
from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.entitlements_selector import entitlements_payload
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.billing import EntitlementsEnvelope, SubscriptionEnvelope
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors import subscription_payload
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router()
logger = logging.getLogger(__name__)


class GooglePlayPurchaseInput(Schema):
    purchase_token: str = Field(min_length=10, max_length=4096)


@router.post(
    "/subscriptions/google-play/purchases",
    operation_id="mobile_api_api_google_play_purchase",
    auth=mobile_bearer,
    response={
        200: SubscriptionEnvelope,
        403: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
        503: ErrorEnvelope,
    },
)
def google_play_purchase(request, payload: GooglePlayPurchaseInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    if not settings.BILLING_GOOGLE_PLAY_PURCHASES_ENABLED:
        raise MobileAPIError(
            code="google_play_purchases_disabled", message="Google Play purchases are not enabled.", status_code=403
        )
    try:
        evidence = build_google_play_gateway().verify_subscription(payload.purchase_token)
        sync_google_play_subscription(evidence, expected_user=request.auth.user)
    except InvalidGooglePlayPurchase as exc:
        raise MobileAPIError(
            code="google_play_purchase_invalid",
            message="The Google Play purchase could not be verified.",
            status_code=422,
        ) from exc
    except GooglePlayEvidenceError as exc:
        raise MobileAPIError(
            code="google_play_purchase_mismatch",
            message="The Google Play purchase does not match this account or product.",
            status_code=409,
        ) from exc
    except GooglePlayConfigurationError as exc:
        raise MobileAPIError(
            code="google_play_billing_unavailable",
            message="Google Play purchase verification is temporarily unavailable.",
            status_code=503,
        ) from exc
    return success(subscription_payload(request.auth.user))


@router.post(
    "/credit-packs/google-play/purchases",
    operation_id="mobile_api_google_play_credit_pack_purchase",
    auth=mobile_bearer,
    response={200: EntitlementsEnvelope, 403: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope, 503: ErrorEnvelope},
)
def google_play_credit_pack_purchase(request, payload: GooglePlayPurchaseInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    if not settings.BILLING_GOOGLE_PLAY_PURCHASES_ENABLED:
        raise MobileAPIError("google_play_purchases_disabled", "Google Play purchases are not enabled.", 403)
    try:
        evidence = build_google_play_gateway().verify_product(payload.purchase_token)
        settle_google_play_credit_pack(user=request.auth.user, evidence=evidence)
    except InvalidGooglePlayPurchase as exc:
        raise MobileAPIError("google_play_purchase_invalid", "The product purchase could not be verified.", 422) from exc
    except CreditPackUnavailable as exc:
        raise MobileAPIError(str(exc), "The credit purchase does not match this account or product.", 409) from exc
    except GooglePlayConfigurationError as exc:
        raise MobileAPIError("google_play_billing_unavailable", "Google Play verification is unavailable.", 503) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected Google Play credit-pack verification failure (token_length=%d)",
            len(payload.purchase_token),
        )
        raise MobileAPIError(
            "google_play_billing_unavailable", "Google Play verification is temporarily unavailable.", 503
        ) from exc
    return success(entitlements_payload(request.auth.user))
