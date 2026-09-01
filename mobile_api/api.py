from __future__ import annotations

from django.conf import settings
from ninja import NinjaAPI
from ninja.errors import AuthenticationError
from ninja.errors import ValidationError as NinjaValidationError

from accounts.forms import AccountDeletionForm, NutritionOnboardingForm
from accounts.services.deletion import delete_user_account
from accounts.services.mobile_disclosures import accept_current_mobile_disclosure
from accounts.services.onboarding import complete_nutrition_onboarding
from ai_assistant.application.async_jobs import AsyncJobContractError, async_jobs_enabled
from ai_assistant.models import AIAsyncJob
from billing.application.services.apple_app_store import AppleEvidenceError, sync_apple_transaction
from billing.infrastructure.gateways import build_apple_app_store_gateway
from billing.infrastructure.providers.apple_app_store import (
    AppleAppStoreConfigurationError,
    InvalidAppleSignedData,
)
from core.rate_limits import is_ai_assistant_turn_rate_limited
from mobile_api.ai_chats import chat_detail_payload, chat_list_payload, completed_turn_payload, pending_turn_job
from mobile_api.api_support import (
    calendarization_error as _calendarization_error,
)
from mobile_api.api_support import (
    food_label_error as _food_label_error,
)
from mobile_api.api_support import (
    form_error as _form_error,
)
from mobile_api.api_support import (
    require_scope as _require_scope,
)
from mobile_api.api_support import (
    success as _success,
)
from mobile_api.auth import mobile_bearer
from mobile_api.composition import (
    add_dailyplan_from_picker,
    add_food_from_picker,
    add_meal_from_picker,
    add_week_from_picker,
    duplicate_program_week,
    preview_dailyplan_for_program,
    preview_food_for_meal,
    preview_meal_for_dailyplan,
    preview_week_for_program,
    remove_dailyplan_from_program,
    remove_food_from_meal,
    remove_meal_from_dailyplan,
    remove_program_week,
    reorder_foods_in_meal,
    reorder_meals_in_dailyplan,
    reorder_weeks_in_program,
    update_food_in_meal,
    update_meal_in_dailyplan,
)
from mobile_api.errors import MobileAPIError, error_envelope
from mobile_api.library_actions import bulk_delete_library, perform_library_action, reorder_library
from mobile_api.routes.calendarization import router as calendarization_router
from mobile_api.routes.comparisons import router as comparisons_router
from mobile_api.routes.composition import router as composition_router
from mobile_api.routes.libraries import router as libraries_router
from mobile_api.routes.proposals import router as proposals_router
from mobile_api.schemas import (
    AccountDeletionEnvelope,
    AccountDeletionInput,
    ActiveProgramEnvelope,
    AIChatDetailEnvelope,
    AIChatListEnvelope,
    AIJobAcceptedEnvelope,
    AIJobResultEnvelope,
    AIPreparedActionResultEnvelope,
    AITurnInput,
    ApplePushRegistrationEnvelope,
    ApplePushRegistrationInput,
    AppleTransactionInput,
    CalendarizationActivationEnvelope,
    CalendarizationActivationInput,
    CalendarizationHistoryEnvelope,
    CalendarizationReviewEnvelope,
    CalendarizationReviewInput,
    CalendarizationReviewListEnvelope,
    CalendarizedDayDetailEnvelope,
    CompositionMutationEnvelope,
    CompositionOrderInput,
    DailyPlanMealUpdateInput,
    DailyPlanPickerInput,
    DisclosureAcceptanceInput,
    EntitlementsEnvelope,
    ErrorEnvelope,
    FoodCreateInput,
    FoodItemEnvelope,
    FoodLabelCaptureEnvelope,
    FoodLabelCaptureInput,
    FoodPageEnvelope,
    FoodPickerInput,
    HealthEnvelope,
    LibraryActionInput,
    LibraryActionResultEnvelope,
    LibraryBulkDeleteInput,
    LibraryItemEnvelope,
    LibraryListActionResultEnvelope,
    LibraryOrderInput,
    LibraryPageEnvelope,
    MealCheckInInput,
    MealFoodUpdateInput,
    MealPickerInput,
    NamedLibraryCreateInput,
    OnboardingInput,
    PickerCommitEnvelope,
    PickerPreviewEnvelope,
    ProfileEnvelope,
    ReminderSettingsEnvelope,
    ReminderSettingsInput,
    RevisionDecisionInput,
    RevisionEnvelope,
    RevisionListEnvelope,
    RevokeSessionEnvelope,
    SessionEnvelope,
    SubscriptionEnvelope,
    TodayEnvelope,
    WeightCreateInput,
    WeightEnvelope,
    WeightListEnvelope,
)
from mobile_api.selectors import (
    active_program_payload,
    calendarization_history_payload,
    calendarized_day_payload,
    entitlements_payload,
    food_label_capture_payload,
    library_dailyplans_payload,
    library_foods_payload,
    library_item_detail_payload,
    library_meals_payload,
    library_programs_payload,
    profile_payload,
    reminder_settings_payload,
    review_payload,
    revision_payload,
    session_payload,
    subscription_payload,
    today_payload,
)
from notas.application.ai_intake.async_turns import enqueue_nutrition_intake_turn
from notas.application.ai_tools.prepared_actions import cancel_prepared_action, commit_prepared_action
from notas.application.queries.food_picker_queries import (
    build_food_picker_item_dto,
    get_food_picker_queryset,
    list_food_picker_page,
)
from notas.application.services.access.capabilities import get_capabilities
from notas.application.services.commands.calendarization_commands import (
    activate_program_calendarization,
    calendarization_empty_dates,
    cancel_calendarization,
    pause_calendarization,
    register_apple_push_subscription,
    resume_calendarization,
    update_calendarization_preferences,
)
from notas.application.services.commands.calendarization_execution_commands import (
    create_calendarization_review,
    decide_calendarization_revision,
    record_calendarized_weight,
    record_meal_execution,
)
from notas.application.services.commands.dailyplan_commands import create_draft_dailyplan
from notas.application.services.commands.food_commands import create_food, create_food_from_label_capture
from notas.application.services.commands.meal_commands import create_draft_meal
from notas.application.services.commands.program_commands import create_weekly_program
from notas.application.services.notifications.apple_push import apns_is_configured
from notas.application.services.oauth_device_sessions import (
    MOBILE_SCOPE_ACCOUNT,
    MOBILE_SCOPE_WRITE,
    revoke_oauth_device_session,
)
from notas.domain.models import (
    AiNutritionChat,
    CalendarizationReview,
    CalendarizationRevision,
    Program,
    ProgramCalendarization,
    SavedComparison,
    WeightLog,
)

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
    "/subscriptions",
    auth=mobile_bearer,
    response={200: SubscriptionEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def subscriptions(request):
    return _success(
        subscription_payload(
            request.auth.user,
            purchases_enabled=settings.BILLING_APPLE_PURCHASES_ENABLED,
        )
    )


@api.post(
    "/subscriptions/apple/transactions",
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
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
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
    return _success(subscription_payload(request.auth.user, purchases_enabled=True))


api.add_router("", calendarization_router)


api.add_router("", proposals_router)


api.add_router("", comparisons_router)


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


@api.post(
    "/account/disclosures",
    auth=mobile_bearer,
    response={200: ProfileEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def accept_disclosures(request, payload: DisclosureAcceptanceInput):
    _require_scope(request.auth, MOBILE_SCOPE_ACCOUNT)
    accept_current_mobile_disclosure(user=request.auth.user)
    return _success(profile_payload(request.auth.user))


api.add_router("", libraries_router)
api.add_router("", composition_router)


@api.post(
    "/ai/turns",
    auth=mobile_bearer,
    response={
        202: AIJobAcceptedEnvelope,
        403: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
        429: ErrorEnvelope,
        503: ErrorEnvelope,
    },
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
    product_context = {}
    if payload.comparison_id is not None:
        comparison = SavedComparison.objects.filter(pk=payload.comparison_id, owner=request.auth.user).first()
        if comparison is None:
            raise MobileAPIError(
                code="saved_comparison_not_found",
                message="The saved comparison was not found.",
                status_code=422,
            )
        snapshot = comparison.snapshot_payload if isinstance(comparison.snapshot_payload, list) else []
        product_context = {
            "saved_comparison_card": {
                "type": "saved_comparison_card",
                "comparison_id": comparison.id,
                "title": comparison.name,
                "kind": comparison.kind,
                "item_count": len(snapshot),
            },
            "saved_comparison": {
                "id": comparison.id,
                "title": comparison.name,
                "kind": comparison.kind,
                "items": [str(row.get("name") or "")[:120] for row in snapshot[:8] if isinstance(row, dict)],
            },
        }
    pending_job = pending_turn_job(request.auth.user, chat_id=chat.id if chat else None)
    if pending_job is not None and pending_job.idempotency_key != payload.idempotency_key:
        raise MobileAPIError(
            code="assistant_turn_pending",
            message="A turn is already being processed for this conversation.",
            status_code=409,
            details={"job_id": str(pending_job.public_id)},
        )
    try:
        job, _created = enqueue_nutrition_intake_turn(
            user=request.auth.user,
            message=payload.message,
            existing_payload=chat.conversation_payload if chat else None,
            existing_chat_id=chat.id if chat else None,
            idempotency_key=payload.idempotency_key,
            product_context=product_context,
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
    "/ai/chats",
    auth=mobile_bearer,
    response={200: AIChatListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def ai_chats(request, offset: int = 0, limit: int = 30):
    return _success(chat_list_payload(request.auth.user, offset=offset, limit=limit))


@api.get(
    "/ai/chats/{chat_id}",
    auth=mobile_bearer,
    response={200: AIChatDetailEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def ai_chat_detail(request, chat_id: int):
    payload = chat_detail_payload(request.auth.user, chat_id)
    if payload is None:
        raise MobileAPIError(code="ai_chat_not_found", message="AI chat was not found.", status_code=404)
    return _success(payload)


def _prepared_action_error(exc: ValueError) -> MobileAPIError:
    code = str(exc)
    status = 404 if code == "prepared_action_not_found" else 409
    return MobileAPIError(code=code, message="The prepared action is no longer available.", status_code=status)


@api.post(
    "/ai/prepared-actions/{action_id}/commit",
    auth=mobile_bearer,
    response={200: AIPreparedActionResultEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope},
)
def commit_ai_prepared_action(request, action_id: str):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        action = commit_prepared_action(user=request.auth.user, public_id=action_id)
    except ValueError as exc:
        raise _prepared_action_error(exc) from exc
    return _success({"action_id": str(action.public_id), "status": action.status, "refresh_chat": True})


@api.post(
    "/ai/prepared-actions/{action_id}/cancel",
    auth=mobile_bearer,
    response={200: AIPreparedActionResultEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope},
)
def cancel_ai_prepared_action(request, action_id: str):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        action = cancel_prepared_action(user=request.auth.user, public_id=action_id)
    except ValueError as exc:
        raise _prepared_action_error(exc) from exc
    return _success({"action_id": str(action.public_id), "status": action.status, "refresh_chat": True})


@api.get(
    "/ai/jobs/{job_id}",
    auth=mobile_bearer,
    response={
        200: AIJobResultEnvelope,
        202: AIJobResultEnvelope,
        401: ErrorEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        422: ErrorEnvelope,
    },
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
        try:
            result = completed_turn_payload(job)
        except ValueError as exc:
            raise MobileAPIError(
                code="assistant_turn_result_invalid",
                message="The assistant turn completed without a valid conversation.",
                status_code=422,
            ) from exc
        return _success(
            {
                "job_id": str(job.public_id),
                "status": job.status,
                "retry_after_ms": None,
                "result": result,
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
