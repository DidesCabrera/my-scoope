from __future__ import annotations

from ninja import NinjaAPI
from ninja.errors import AuthenticationError
from ninja.errors import ValidationError as NinjaValidationError

from accounts.forms import AccountDeletionForm, NutritionOnboardingForm
from accounts.services.deletion import delete_user_account
from accounts.services.onboarding import complete_nutrition_onboarding
from ai_assistant.application.async_jobs import AsyncJobContractError, async_jobs_enabled
from ai_assistant.models import AIAsyncJob
from core.rate_limits import is_ai_assistant_turn_rate_limited
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError, error_envelope
from mobile_api.schemas import (
    AccountDeletionEnvelope,
    AccountDeletionInput,
    ActiveProgramEnvelope,
    AIJobAcceptedEnvelope,
    AIJobResultEnvelope,
    AITurnInput,
    EntitlementsEnvelope,
    ErrorEnvelope,
    FoodPageEnvelope,
    HealthEnvelope,
    OnboardingInput,
    ProfileEnvelope,
    RevokeSessionEnvelope,
    SessionEnvelope,
    TodayEnvelope,
    WeightCreateInput,
    WeightEnvelope,
    WeightListEnvelope,
)
from mobile_api.selectors import (
    active_program_payload,
    entitlements_payload,
    profile_payload,
    session_payload,
    today_payload,
)
from notas.application.ai_intake.async_turns import enqueue_nutrition_intake_turn
from notas.application.queries.food_picker_queries import list_food_picker_page
from notas.application.services.nutrition.body_metrics import record_weight
from notas.application.services.oauth_device_sessions import (
    MOBILE_SCOPE_ACCOUNT,
    MOBILE_SCOPE_WRITE,
    revoke_oauth_device_session,
)
from notas.domain.models import AiNutritionChat, WeightLog

api = NinjaAPI(
    title="My Scoope Consumer API",
    version="1.0.0",
    description="Versioned screen-oriented API for the My Scoope consumer mobile client.",
    urls_namespace="mobile_api_v1",
)


@api.exception_handler(MobileAPIError)
def handle_mobile_api_error(request, exc):
    return api.create_response(request, error_envelope(exc), status=exc.status_code)


@api.exception_handler(NinjaValidationError)
def handle_validation_error(request, exc):
    error = MobileAPIError(
        code="request_validation_failed",
        message="Request payload or parameters are invalid.",
        status_code=422,
        details={"errors": exc.errors},
    )
    return api.create_response(request, error_envelope(error), status=422)


@api.exception_handler(AuthenticationError)
def handle_authentication_error(request, exc):
    error = MobileAPIError(
        code="mobile_auth_required",
        message="A valid mobile bearer token is required.",
        status_code=401,
    )
    return api.create_response(request, error_envelope(error), status=401)


def _success(data: dict) -> dict:
    return {"ok": True, "data": data, "error": None}


def _require_scope(auth, scope: str) -> None:
    if scope not in auth.token.scopes:
        raise MobileAPIError(
            code="mobile_scope_missing",
            message="The access token does not include the required mobile scope.",
            status_code=403,
            details={"required_scope": scope},
        )


def _form_error(form, *, code: str, message: str) -> MobileAPIError:
    return MobileAPIError(
        code=code,
        message=message,
        status_code=422,
        details={"fields": form.errors.get_json_data()},
    )


@api.get("/health", auth=None, response={200: HealthEnvelope})
def health(request):
    return _success({"status": "ok", "api_version": "v1"})


@api.get("/session", auth=mobile_bearer, response={200: SessionEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope})
def session(request):
    return _success(session_payload(request.auth))


@api.delete(
    "/sessions/{device_session_id}",
    auth=mobile_bearer,
    response={200: RevokeSessionEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def revoke_session(request, device_session_id: str):
    _require_scope(request.auth, MOBILE_SCOPE_ACCOUNT)
    revoked = revoke_oauth_device_session(user=request.auth.user, public_id=device_session_id)
    if not revoked:
        raise MobileAPIError(
            code="device_session_not_found",
            message="Device session was not found.",
            status_code=404,
        )
    return _success({"revoked": True, "device_session_id": device_session_id})


@api.get("/me", auth=mobile_bearer, response={200: ProfileEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope})
def me(request):
    return _success(profile_payload(request.auth.user))


@api.post(
    "/onboarding",
    auth=mobile_bearer,
    response={200: ProfileEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def onboarding(request, payload: OnboardingInput):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    form = NutritionOnboardingForm(
        {
            "birth_date": payload.birth_date.isoformat(),
            "sex": payload.sex,
            "height_cm": payload.height_cm,
            "weight_kg": payload.weight_kg,
        }
    )
    if not form.is_valid():
        raise _form_error(form, code="onboarding_invalid", message="Onboarding data is invalid.")
    complete_nutrition_onboarding(
        user=request.auth.user,
        birth_date=form.cleaned_data["birth_date"],
        sex=form.cleaned_data["sex"],
        height_cm=form.cleaned_data["height_cm"],
        weight_kg=form.cleaned_data["weight_kg"],
    )
    return _success(profile_payload(request.auth.user))


@api.get(
    "/entitlements",
    auth=mobile_bearer,
    response={200: EntitlementsEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def entitlements(request):
    return _success(entitlements_payload(request.auth.user))


@api.get(
    "/program/active",
    auth=mobile_bearer,
    response={200: ActiveProgramEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def active_program(request):
    return _success(active_program_payload(request.auth.user))


@api.get("/today", auth=mobile_bearer, response={200: TodayEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope})
def today(request):
    return _success(today_payload(request.auth.user))


@api.get(
    "/weights",
    auth=mobile_bearer,
    response={200: WeightListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def weights(request, limit: int = 30):
    safe_limit = min(max(limit, 1), 100)
    queryset = WeightLog.objects.filter(user=request.auth.user).order_by("-date", "-created_at")[:safe_limit]
    items = [
        {
            "id": item.id,
            "measured_on": item.date,
            "weight_kg": item.weight_kg,
            "source": item.source,
            "created_at": item.created_at,
        }
        for item in queryset
    ]
    return _success({"items": items, "count": len(items)})


@api.post(
    "/weights",
    auth=mobile_bearer,
    response={200: WeightEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def create_weight(request, payload: WeightCreateInput):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    item = record_weight(
        request.auth.user,
        payload.weight_kg,
        measured_on=payload.measured_on,
        source=WeightLog.SOURCE_MANUAL,
    )
    return _success(
        {
            "id": item.id,
            "measured_on": item.date,
            "weight_kg": item.weight_kg,
            "source": item.source,
            "created_at": item.created_at,
        }
    )


@api.post(
    "/account/delete",
    auth=mobile_bearer,
    response={200: AccountDeletionEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def delete_account(request, payload: AccountDeletionInput):
    _require_scope(request.auth, MOBILE_SCOPE_ACCOUNT)
    form = AccountDeletionForm(
        {"confirmation": payload.confirmation, "password": payload.password},
        user=request.auth.user,
    )
    if not form.is_valid():
        raise _form_error(
            form,
            code="account_deletion_confirmation_invalid",
            message="Account deletion could not be confirmed.",
        )
    result = delete_user_account(user=request.auth.user, source="self_service_mobile_api")
    return _success({"receipt_id": str(result.receipt_id)})


@api.get(
    "/foods",
    auth=mobile_bearer,
    response={200: FoodPageEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def foods(request, search: str | None = None, offset: int = 0, limit: int = 30):
    page = list_food_picker_page(
        user=request.auth.user,
        search=search,
        offset=max(offset, 0),
        limit=min(max(limit, 1), 100),
    )
    return _success(
        {
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "display_name": item.display_name,
                    "protein": item.protein,
                    "carbs": item.carbs,
                    "fat": item.fat,
                    "total_kcal": item.total_kcal,
                    "source": item.source,
                    "is_user_food": item.is_user_food,
                    "is_verified": item.is_verified,
                    "data_quality_score": item.data_quality_score,
                }
                for item in page.foods
            ],
            "total": page.total,
            "offset": page.offset,
            "limit": page.limit,
            "search": page.search,
        }
    )


@api.post(
    "/ai/turns",
    auth=mobile_bearer,
    response={202: AIJobAcceptedEnvelope, 403: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope, 429: ErrorEnvelope, 503: ErrorEnvelope},
)
def submit_ai_turn(request, payload: AITurnInput):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    if is_ai_assistant_turn_rate_limited(request):
        raise MobileAPIError(
            code="ai_turn_rate_limited",
            message="Too many assistant turns were submitted. Try again later.",
            status_code=429,
        )
    if not async_jobs_enabled():
        raise MobileAPIError(
            code="ai_async_unavailable",
            message="The durable AI queue is not available.",
            status_code=503,
        )
    chat = None
    if payload.chat_id is not None:
        chat = AiNutritionChat.objects.filter(id=payload.chat_id, user=request.auth.user).first()
        if chat is None:
            raise MobileAPIError(
                code="ai_chat_not_found",
                message="AI chat was not found.",
                status_code=422,
            )
    try:
        job, _created = enqueue_nutrition_intake_turn(
            user=request.auth.user,
            message=payload.message,
            existing_payload=chat.conversation_payload if chat else None,
            existing_chat_id=chat.id if chat else None,
            idempotency_key=payload.idempotency_key,
        )
    except AsyncJobContractError as exc:
        status_code = 409 if exc.code == "idempotency_conflict" else 422
        raise MobileAPIError(
            code=exc.code,
            message=str(exc),
            status_code=status_code,
        ) from exc
    return 202, _success(
        {
            "job_id": str(job.public_id),
            "status": job.status,
            "retry_after_ms": 750,
        }
    )


@api.get(
    "/ai/jobs/{job_id}",
    auth=mobile_bearer,
    response={200: AIJobResultEnvelope, 202: AIJobResultEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def ai_job(request, job_id: str):
    try:
        job = AIAsyncJob.objects.get(public_id=job_id, user=request.auth.user)
    except (AIAsyncJob.DoesNotExist, ValueError):
        raise MobileAPIError(
            code="ai_job_not_found",
            message="AI job was not found.",
            status_code=404,
        ) from None
    if job.status in {AIAsyncJob.Status.FAILED, AIAsyncJob.Status.CANCELLED}:
        raise MobileAPIError(
            code="assistant_turn_failed",
            message="The assistant turn could not be completed.",
            status_code=422,
            details={"status": job.status, "retryable": False},
        )
    if job.status == AIAsyncJob.Status.SUCCEEDED:
        return _success(
            {
                "job_id": str(job.public_id),
                "status": job.status,
                "retry_after_ms": None,
                "result": dict(job.result_payload or {}),
            }
        )
    return 202, _success(
        {
            "job_id": str(job.public_id),
            "status": job.status,
            "retry_after_ms": 750,
            "result": None,
        }
    )
