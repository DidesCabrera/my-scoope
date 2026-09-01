from __future__ import annotations

from ninja import Router

from accounts.forms import AccountDeletionForm, NutritionOnboardingForm
from accounts.services.deletion import delete_user_account
from accounts.services.mobile_disclosures import accept_current_mobile_disclosure
from accounts.services.onboarding import complete_nutrition_onboarding
from mobile_api.api_support import form_error, require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.identity import (
    AccountDeletionEnvelope,
    AccountDeletionInput,
    DisclosureAcceptanceInput,
    OnboardingInput,
    ProfileEnvelope,
    RevokeSessionEnvelope,
    SessionEnvelope,
)
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors import profile_payload, session_payload
from notas.application.services.oauth_device_sessions import (
    MOBILE_SCOPE_ACCOUNT,
    MOBILE_SCOPE_WRITE,
    revoke_oauth_device_session,
)

router = Router()


@router.get(
    "/session",
    operation_id="mobile_api_api_session",
    auth=mobile_bearer,
    response={200: SessionEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def session(request):
    return success(session_payload(request.auth))


@router.delete(
    "/sessions/{device_session_id}",
    operation_id="mobile_api_api_revoke_session",
    auth=mobile_bearer,
    response={200: RevokeSessionEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def revoke_session(request, device_session_id: str):
    require_scope(request.auth, MOBILE_SCOPE_ACCOUNT)
    revoked = revoke_oauth_device_session(user=request.auth.user, public_id=device_session_id)
    if not revoked:
        raise MobileAPIError(
            code="device_session_not_found",
            message="Device session was not found.",
            status_code=404,
        )
    return success({"revoked": True, "device_session_id": device_session_id})


@router.get(
    "/me",
    operation_id="mobile_api_api_me",
    auth=mobile_bearer,
    response={200: ProfileEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def me(request):
    return success(profile_payload(request.auth.user))


@router.post(
    "/onboarding",
    operation_id="mobile_api_api_onboarding",
    auth=mobile_bearer,
    response={200: ProfileEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def onboarding(request, payload: OnboardingInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    form = NutritionOnboardingForm(
        {
            "birth_date": payload.birth_date.isoformat(),
            "sex": payload.sex,
            "height_cm": payload.height_cm,
            "weight_kg": payload.weight_kg,
        }
    )
    if not form.is_valid():
        raise form_error(form, code="onboarding_invalid", message="Onboarding data is invalid.")
    complete_nutrition_onboarding(
        user=request.auth.user,
        birth_date=form.cleaned_data["birth_date"],
        sex=form.cleaned_data["sex"],
        height_cm=form.cleaned_data["height_cm"],
        weight_kg=form.cleaned_data["weight_kg"],
    )
    return success(profile_payload(request.auth.user))


@router.post(
    "/account/delete",
    operation_id="mobile_api_api_delete_account",
    auth=mobile_bearer,
    response={200: AccountDeletionEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def delete_account(request, payload: AccountDeletionInput):
    require_scope(request.auth, MOBILE_SCOPE_ACCOUNT)
    form = AccountDeletionForm(
        {"confirmation": payload.confirmation, "password": payload.password},
        user=request.auth.user,
    )
    if not form.is_valid():
        raise form_error(
            form,
            code="account_deletion_confirmation_invalid",
            message="Account deletion could not be confirmed.",
        )
    result = delete_user_account(user=request.auth.user, source="self_service_mobile_api")
    return success({"receipt_id": str(result.receipt_id)})


@router.post(
    "/account/disclosures",
    operation_id="mobile_api_api_accept_disclosures",
    auth=mobile_bearer,
    response={200: ProfileEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def accept_disclosures(request, payload: DisclosureAcceptanceInput):
    require_scope(request.auth, MOBILE_SCOPE_ACCOUNT)
    accept_current_mobile_disclosure(user=request.auth.user)
    return success(profile_payload(request.auth.user))
