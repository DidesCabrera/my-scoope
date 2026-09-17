from django.conf import settings
from ninja import Field, Router, Schema

from billing.application.services.google_play import GooglePlayEvidenceError, sync_google_play_subscription
from billing.infrastructure.gateways import build_google_play_gateway
from billing.infrastructure.providers.google_play import GooglePlayConfigurationError, InvalidGooglePlayPurchase
from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.billing import SubscriptionEnvelope
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors import subscription_payload
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router()


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
