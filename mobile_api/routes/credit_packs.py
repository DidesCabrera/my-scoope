"""Store purchase evidence for consumable credit packs."""

from ninja import Router

from billing.application.services.credit_packs import CreditPackUnavailable, settle_apple_credit_pack
from billing.infrastructure.providers.apple_app_store import AppleAppStoreConfigurationError, InvalidAppleSignedData
from mobile_api.api_support import require_scope, success
from mobile_api.apple_billing import apple_purchases_enabled_for_user, verify_apple_transaction_for_user
from mobile_api.auth import mobile_bearer
from mobile_api.entitlements_selector import entitlements_payload
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.billing import AppleTransactionInput, EntitlementsEnvelope
from mobile_api.schemas import ErrorEnvelope
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router()


@router.post(
    "/credit-packs/apple/transactions",
    operation_id="mobile_api_apple_credit_pack_transaction",
    auth=mobile_bearer,
    response={200: EntitlementsEnvelope, 403: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope, 503: ErrorEnvelope},
)
def apple_credit_pack_transaction(request, payload: AppleTransactionInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    if not apple_purchases_enabled_for_user(request.auth.user):
        raise MobileAPIError("apple_purchases_disabled", "Apple purchases are not enabled.", 403)
    try:
        evidence = verify_apple_transaction_for_user(payload.signed_transaction, user=request.auth.user)
        settle_apple_credit_pack(user=request.auth.user, evidence=evidence)
    except InvalidAppleSignedData as exc:
        raise MobileAPIError("apple_transaction_invalid", "The StoreKit transaction could not be verified.", 422) from exc
    except CreditPackUnavailable as exc:
        raise MobileAPIError(str(exc), "The credit purchase does not match this account or product.", 409) from exc
    except AppleAppStoreConfigurationError as exc:
        raise MobileAPIError("apple_billing_unavailable", "Apple verification is unavailable.", 503) from exc
    return success(entitlements_payload(request.auth.user))
