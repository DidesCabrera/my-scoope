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
from mobile_api.auth import mobile_bearer
from mobile_api.comparisons import (
    comparison_metadata_payload,
    comparison_options_payload,
    dynamic_comparison_payload,
    save_comparison,
    saved_comparison_detail_payload,
    saved_comparison_list_payload,
    update_comparison,
)
from mobile_api.errors import MobileAPIError, error_envelope
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
    ComparisonMetadataEnvelope,
    ComparisonOptionsEnvelope,
    ComparisonRequestInput,
    ComparisonResultEnvelope,
    DisclosureAcceptanceInput,
    EntitlementsEnvelope,
    ErrorEnvelope,
    FoodLabelCaptureEnvelope,
    FoodLabelCaptureInput,
    FoodPageEnvelope,
    HealthEnvelope,
    LibraryItemEnvelope,
    LibraryPageEnvelope,
    MealCheckInInput,
    OnboardingInput,
    ProfileEnvelope,
    ProposalApplyInput,
    ProposalDetailEnvelope,
    ProposalListEnvelope,
    ReminderSettingsEnvelope,
    ReminderSettingsInput,
    RevisionDecisionInput,
    RevisionEnvelope,
    RevisionListEnvelope,
    RevokeSessionEnvelope,
    SavedComparisonDetailEnvelope,
    SavedComparisonListEnvelope,
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
    proposal_detail_payload,
    proposal_list_payload,
    reminder_settings_payload,
    review_payload,
    revision_payload,
    session_payload,
    subscription_payload,
    today_payload,
)
from notas.application.ai_intake.async_turns import enqueue_nutrition_intake_turn
from notas.application.ai_tools.prepared_actions import cancel_prepared_action, commit_prepared_action
from notas.application.proposals.contracts import (
    CREATE_DAILYPLAN_INTENT,
    CREATE_MEAL_INTENT,
    resolve_proposal_intent,
)
from notas.application.proposals.subject_context_warnings import (
    proposal_requires_external_subject_ack,
)
from notas.application.queries.food_picker_queries import list_food_picker_page
from notas.application.queries.proposal_queries import get_available_proposal_queryset
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
from notas.application.services.commands.food_commands import create_food_from_label_capture
from notas.application.services.commands.proposal_commands import (
    apply_approved_create_dailyplan_proposal,
    apply_approved_create_meal_proposal,
    approve_proposal,
    cancel_proposal,
    reject_proposal,
)
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


def _calendarization_error(exc: ValueError) -> MobileAPIError:
    code = str(exc)
    not_found = {
        "calendarization_not_found",
        "calendarized_day_not_found",
        "calendarization_revision_not_found",
        "calendarization_review_not_found",
        "calendarization_program_not_owned",
    }
    conflicts = {
        "calendarization_idempotency_conflict",
        "calendarization_revision_already_decided",
        "calendarization_revision_no_longer_eligible",
        "calendarization_incomplete_confirmation_required",
        "calendarization_replacement_confirmation_required",
        "calendarization_current_conflict",
        "calendarization_cannot_pause",
        "calendarization_cannot_resume",
        "calendarization_cannot_cancel",
    }
    return MobileAPIError(
        code=code,
        message="The lived-program operation could not be completed.",
        status_code=404 if code in not_found else 409 if code in conflicts else 422,
    )


def _food_label_error(exc: ValueError) -> MobileAPIError:
    code = str(exc)
    return MobileAPIError(
        code=code,
        message="The confirmed nutrition label could not be saved.",
        status_code=409 if code == "food_label_idempotency_conflict" else 422,
    )


def _proposal_error(exc: ValueError) -> MobileAPIError:
    code = str(exc)
    not_found = {
        "proposal_not_found",
        "proposal_review_not_allowed",
        "proposal_cancel_not_allowed",
    }
    conflicts = {
        "proposal_is_not_pending_review",
        "proposal_is_not_applicable",
        "proposal_apply_requires_applicable_status",
        "proposal_already_applied",
        "proposal_is_final",
        "proposal_external_subject_ack_required",
        "proposal_apply_not_supported",
    }
    return MobileAPIError(
        code=code,
        message="No pudimos completar la operación de la propuesta.",
        status_code=404 if code in not_found else 409 if code in conflicts else 422,
    )


def _comparison_error(exc: ValueError) -> MobileAPIError:
    code = str(exc)
    not_found = {"comparison_item_not_available", "saved_comparison_not_found"}
    conflicts = {"saved_comparison_kind_mismatch"}
    return MobileAPIError(
        code=code,
        message="No pudimos completar la comparación.",
        status_code=404 if code in not_found else 409 if code in conflicts else 422,
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


@api.get(
    "/program/active",
    auth=mobile_bearer,
    response={200: ActiveProgramEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def active_program(request):
    return _success(active_program_payload(request.auth.user))


@api.post(
    "/program/calendarizations",
    auth=mobile_bearer,
    response={200: CalendarizationActivationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def activate_calendarization(request, payload: CalendarizationActivationInput):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    program = Program.objects.filter(pk=payload.program_id, created_by=request.auth.user).first()
    if program is None:
        raise _calendarization_error(ValueError("calendarization_program_not_owned"))
    try:
        result = activate_program_calendarization(
            user=request.auth.user,
            program=program,
            start_date=payload.start_date,
            timezone_name=payload.timezone_name,
            daily_notification_time=payload.daily_notification_time,
            daily_notifications_enabled=payload.daily_notifications_enabled,
            meal_notifications_enabled=payload.meal_notifications_enabled,
            confirm_incomplete=payload.confirm_incomplete,
            replace_current=payload.replace_current,
        )
    except ValueError as exc:
        error = _calendarization_error(exc)
        if str(exc) == "calendarization_incomplete_confirmation_required":
            empty_dates = calendarization_empty_dates(program=program, start_date=payload.start_date)
            error = MobileAPIError(
                code=error.code,
                message=error.message,
                status_code=error.status_code,
                details={
                    "empty_count": len(empty_dates),
                    "empty_dates": [value.isoformat() for value in empty_dates],
                },
            )
        elif str(exc) == "calendarization_replacement_confirmation_required":
            current = ProgramCalendarization.objects.filter(
                user=request.auth.user,
                status__in=ProgramCalendarization.CURRENT_STATUSES,
            ).first()
            error = MobileAPIError(
                code=error.code,
                message=error.message,
                status_code=error.status_code,
                details={
                    "current_calendarization_id": current.id if current else None,
                    "current_program_name": current.program_name_snapshot if current else "",
                },
            )
        raise error from exc
    response = active_program_payload(request.auth.user)
    response.update(
        {
            "empty_dates": list(result.empty_dates),
            "replaced_calendarization_id": result.replaced_calendarization_id,
        }
    )
    return _success(response)


@api.get(
    "/program/calendarizations/history",
    auth=mobile_bearer,
    response={200: CalendarizationHistoryEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def calendarization_history(request, limit: int = 20):
    return _success(calendarization_history_payload(request.auth.user, limit=limit))


@api.get(
    "/program/days/{day_id}",
    auth=mobile_bearer,
    response={200: CalendarizedDayDetailEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def calendarized_day_detail(request, day_id: int):
    day = calendarized_day_payload(request.auth.user, day_id)
    if day is None:
        raise _calendarization_error(ValueError("calendarized_day_not_found"))
    return _success(day)


def _calendarization_state_action(request, calendarization_id: int, command):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        command(user=request.auth.user, calendarization_id=calendarization_id)
    except ValueError as exc:
        raise _calendarization_error(exc) from exc
    return _success(active_program_payload(request.auth.user))


@api.post(
    "/program/calendarizations/{calendarization_id}/pause",
    auth=mobile_bearer,
    response={200: ActiveProgramEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def pause_active_calendarization(request, calendarization_id: int):
    return _calendarization_state_action(request, calendarization_id, pause_calendarization)


@api.post(
    "/program/calendarizations/{calendarization_id}/resume",
    auth=mobile_bearer,
    response={200: ActiveProgramEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def resume_active_calendarization(request, calendarization_id: int):
    return _calendarization_state_action(request, calendarization_id, resume_calendarization)


@api.post(
    "/program/calendarizations/{calendarization_id}/cancel",
    auth=mobile_bearer,
    response={200: ActiveProgramEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def cancel_active_calendarization(request, calendarization_id: int):
    return _calendarization_state_action(request, calendarization_id, cancel_calendarization)


def _owned_proposal(user, proposal_id: int):
    proposal = get_available_proposal_queryset(user).filter(pk=proposal_id).first()
    if proposal is None:
        raise _proposal_error(ValueError("proposal_not_found"))
    return proposal


@api.get(
    "/proposals",
    auth=mobile_bearer,
    response={200: ProposalListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def proposals(request, status: str | None = None, offset: int = 0, limit: int = 30):
    return _success(proposal_list_payload(request.auth.user, status_filter=status, offset=offset, limit=limit))


@api.get(
    "/proposals/{proposal_id}",
    auth=mobile_bearer,
    response={200: ProposalDetailEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def proposal_detail(request, proposal_id: int):
    payload = proposal_detail_payload(request.auth.user, proposal_id)
    if payload is None:
        raise _proposal_error(ValueError("proposal_not_found"))
    return _success(payload)


def _proposal_state_action(request, proposal_id: int, command):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    proposal = _owned_proposal(request.auth.user, proposal_id)
    try:
        command(user=request.auth.user, proposal=proposal)
    except ValueError as exc:
        raise _proposal_error(exc) from exc
    return _success(proposal_detail_payload(request.auth.user, proposal_id))


@api.post(
    "/proposals/{proposal_id}/approve",
    auth=mobile_bearer,
    response={200: ProposalDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def approve_mobile_proposal(request, proposal_id: int):
    return _proposal_state_action(request, proposal_id, approve_proposal)


@api.post(
    "/proposals/{proposal_id}/reject",
    auth=mobile_bearer,
    response={200: ProposalDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def reject_mobile_proposal(request, proposal_id: int):
    return _proposal_state_action(request, proposal_id, reject_proposal)


@api.post(
    "/proposals/{proposal_id}/cancel",
    auth=mobile_bearer,
    response={200: ProposalDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def cancel_mobile_proposal(request, proposal_id: int):
    return _proposal_state_action(request, proposal_id, cancel_proposal)


@api.post(
    "/proposals/{proposal_id}/apply",
    auth=mobile_bearer,
    response={200: ProposalDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def apply_mobile_proposal(request, proposal_id: int, payload: ProposalApplyInput):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    proposal = _owned_proposal(request.auth.user, proposal_id)
    if proposal_requires_external_subject_ack(proposal) and not payload.acknowledge_external_subject:
        raise _proposal_error(ValueError("proposal_external_subject_ack_required"))
    intent = resolve_proposal_intent(proposal.proposed_payload)
    try:
        if intent == CREATE_MEAL_INTENT:
            apply_approved_create_meal_proposal(user=request.auth.user, proposal=proposal)
        elif intent == CREATE_DAILYPLAN_INTENT:
            apply_approved_create_dailyplan_proposal(user=request.auth.user, proposal=proposal)
        else:
            raise ValueError("proposal_apply_not_supported")
    except ValueError as exc:
        raise _proposal_error(exc) from exc
    return _success(proposal_detail_payload(request.auth.user, proposal_id))


@api.get(
    "/comparisons/metadata",
    auth=mobile_bearer,
    response={200: ComparisonMetadataEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def comparison_metadata(request):
    return _success(comparison_metadata_payload())


@api.get(
    "/comparisons/options/{kind}",
    auth=mobile_bearer,
    response={200: ComparisonOptionsEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def comparison_options(request, kind: str, search: str | None = None, offset: int = 0, limit: int = 30):
    try:
        payload = comparison_options_payload(
            request.auth.user,
            kind=kind,
            search=search,
            offset=offset,
            limit=limit,
        )
    except ValueError as exc:
        raise _comparison_error(exc) from exc
    return _success(payload)


def _comparison_selections(payload: ComparisonRequestInput) -> list[dict]:
    return [
        {"id": selection.id, "quantity": selection.quantity}
        for selection in payload.selections
    ]


@api.post(
    "/comparisons/compare",
    auth=mobile_bearer,
    response={200: ComparisonResultEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def compare_entities(request, payload: ComparisonRequestInput):
    try:
        result = dynamic_comparison_payload(
            request.auth.user,
            kind=payload.kind,
            selections=_comparison_selections(payload),
        )
    except ValueError as exc:
        raise _comparison_error(exc) from exc
    return _success(result)


@api.get(
    "/comparisons/saved",
    auth=mobile_bearer,
    response={200: SavedComparisonListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def saved_comparisons(request, kind: str | None = None, offset: int = 0, limit: int = 30):
    try:
        payload = saved_comparison_list_payload(
            request.auth.user,
            kind=kind,
            offset=offset,
            limit=limit,
        )
    except ValueError as exc:
        raise _comparison_error(exc) from exc
    return _success(payload)


@api.post(
    "/comparisons/saved",
    auth=mobile_bearer,
    response={200: SavedComparisonDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def create_mobile_saved_comparison(request, payload: ComparisonRequestInput):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        comparison = save_comparison(
            request.auth.user,
            kind=payload.kind,
            selections=_comparison_selections(payload),
        )
    except ValueError as exc:
        raise _comparison_error(exc) from exc
    return _success(saved_comparison_detail_payload(request.auth.user, comparison.id))


@api.get(
    "/comparisons/saved/{comparison_id}",
    auth=mobile_bearer,
    response={200: SavedComparisonDetailEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def saved_comparison_detail(request, comparison_id: int):
    payload = saved_comparison_detail_payload(request.auth.user, comparison_id)
    if payload is None:
        raise _comparison_error(ValueError("saved_comparison_not_found"))
    return _success(payload)


@api.put(
    "/comparisons/saved/{comparison_id}",
    auth=mobile_bearer,
    response={200: SavedComparisonDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def update_mobile_saved_comparison(request, comparison_id: int, payload: ComparisonRequestInput):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        comparison = update_comparison(
            request.auth.user,
            comparison_id=comparison_id,
            kind=payload.kind,
            selections=_comparison_selections(payload),
        )
    except ValueError as exc:
        raise _comparison_error(exc) from exc
    return _success(saved_comparison_detail_payload(request.auth.user, comparison.id))


@api.get("/today", auth=mobile_bearer, response={200: TodayEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope})
def today(request):
    return _success(today_payload(request.auth.user))


@api.post(
    "/days/{day_id}/meals/{meal_snapshot_key}/check-ins",
    auth=mobile_bearer,
    response={200: TodayEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def meal_check_in(request, day_id: int, meal_snapshot_key: str, payload: MealCheckInInput):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        record_meal_execution(
            user=request.auth.user,
            day_id=day_id,
            meal_snapshot_key=meal_snapshot_key,
            action=payload.action,
            idempotency_key=payload.idempotency_key,
            note=payload.note,
        )
    except ValueError as exc:
        raise _calendarization_error(exc) from exc
    return _success(today_payload(request.auth.user))


@api.put(
    "/program/active/reminders",
    auth=mobile_bearer,
    response={200: ReminderSettingsEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def update_active_program_reminders(request, payload: ReminderSettingsInput):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    calendarization = ProgramCalendarization.objects.filter(
        user=request.auth.user,
        status__in=ProgramCalendarization.CURRENT_STATUSES,
    ).first()
    if calendarization is None:
        raise _calendarization_error(ValueError("calendarization_not_found"))
    try:
        calendarization = update_calendarization_preferences(
            user=request.auth.user,
            calendarization_id=calendarization.id,
            timezone_name=payload.timezone_name,
            daily_notification_time=payload.daily_notification_time,
            daily_notifications_enabled=payload.daily_notifications_enabled,
            meal_notifications_enabled=payload.meal_notifications_enabled,
        )
    except ValueError as exc:
        raise _calendarization_error(exc) from exc
    return _success(reminder_settings_payload(calendarization))


@api.put(
    "/notifications/apple/device",
    auth=mobile_bearer,
    response={200: ApplePushRegistrationEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def register_apple_notification_device(request, payload: ApplePushRegistrationInput):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    device_session = request.auth.token.device_session
    if device_session is None:
        raise MobileAPIError(
            code="apns_device_session_required",
            message="A native mobile device session is required.",
            status_code=422,
        )
    try:
        subscription = register_apple_push_subscription(
            user=request.auth.user,
            device_session=device_session,
            device_token=payload.device_token,
            environment=payload.environment,
        )
    except ValueError as exc:
        raise MobileAPIError(
            code=str(exc),
            message="The Apple notification device could not be registered.",
            status_code=422,
        ) from exc
    return _success(
        {
            "delivery_mode": "apns" if apns_is_configured() else "local",
            "token_fingerprint": subscription.token_fingerprint,
            "environment": subscription.environment,
            "is_active": subscription.is_active,
        }
    )


@api.get(
    "/program/reviews",
    auth=mobile_bearer,
    response={200: CalendarizationReviewListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def program_reviews(request, limit: int = 12):
    items = CalendarizationReview.objects.filter(calendarization__user=request.auth.user).order_by(
        "-period_end", "-created_at", "-id"
    )[: min(max(limit, 1), 50)]
    payload = [review_payload(item) for item in items]
    return _success({"items": payload, "count": len(payload)})


@api.post(
    "/program/reviews",
    auth=mobile_bearer,
    response={200: CalendarizationReviewEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def create_program_review(request, payload: CalendarizationReviewInput):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        review = create_calendarization_review(
            user=request.auth.user,
            period_start=payload.period_start,
            period_end=payload.period_end,
            idempotency_key=payload.idempotency_key,
            energy_score=payload.energy_score,
            hunger_score=payload.hunger_score,
            training_performance_score=payload.training_performance_score,
            note=payload.note,
        )
    except ValueError as exc:
        raise _calendarization_error(exc) from exc
    return _success(review_payload(review))


@api.get(
    "/program/revisions",
    auth=mobile_bearer,
    response={200: RevisionListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def program_revisions(request, limit: int = 12):
    revisions = CalendarizationRevision.objects.filter(calendarization__user=request.auth.user).order_by(
        "-created_at", "-id"
    )[: min(max(limit, 1), 50)]
    payload = [revision_payload(item) for item in revisions]
    return _success({"items": payload, "count": len(payload)})


@api.post(
    "/program/revisions/{revision_id}/decision",
    auth=mobile_bearer,
    response={200: RevisionEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def decide_program_revision(request, revision_id: int, payload: RevisionDecisionInput):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        revision = decide_calendarization_revision(
            user=request.auth.user,
            revision_id=revision_id,
            decision=payload.decision,
        )
    except ValueError as exc:
        raise _calendarization_error(exc) from exc
    return _success(revision_payload(revision))


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
    item, context = record_calendarized_weight(
        user=request.auth.user,
        weight_kg=payload.weight_kg,
        measured_on=payload.measured_on,
    )
    return _success(
        {
            "id": item.id,
            "measured_on": item.date,
            "weight_kg": item.weight_kg,
            "source": item.source,
            "created_at": item.created_at,
            "calendarization_id": context.calendarization_id if context else None,
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


@api.post(
    "/account/disclosures",
    auth=mobile_bearer,
    response={200: ProfileEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def accept_disclosures(request, payload: DisclosureAcceptanceInput):
    _require_scope(request.auth, MOBILE_SCOPE_ACCOUNT)
    accept_current_mobile_disclosure(user=request.auth.user)
    return _success(profile_payload(request.auth.user))


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


@api.get("/library/programs", auth=mobile_bearer, response={200: LibraryPageEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope})
def library_programs(request, search: str | None = None, offset: int = 0, limit: int = 30):
    return _success(library_programs_payload(request.auth.user, search=search, offset=offset, limit=limit))


@api.get("/library/daily-plans", auth=mobile_bearer, response={200: LibraryPageEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope})
def library_dailyplans(request, search: str | None = None, offset: int = 0, limit: int = 30):
    return _success(library_dailyplans_payload(request.auth.user, search=search, offset=offset, limit=limit))


@api.get("/library/meals", auth=mobile_bearer, response={200: LibraryPageEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope})
def library_meals(request, search: str | None = None, offset: int = 0, limit: int = 30):
    return _success(library_meals_payload(request.auth.user, search=search, offset=offset, limit=limit))


@api.get("/library/foods", auth=mobile_bearer, response={200: LibraryPageEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope})
def library_foods(request, search: str | None = None, offset: int = 0, limit: int = 30):
    return _success(library_foods_payload(request.auth.user, search=search, offset=offset, limit=limit))


@api.get("/library/{entity}/{item_id}", auth=mobile_bearer, response={200: LibraryItemEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope})
def library_item_detail(request, entity: str, item_id: int):
    if entity not in {"programs", "daily-plans", "meals", "foods"}:
        raise MobileAPIError(code="library_item_not_found", message="The requested library item was not found.", status_code=404)
    return _success(library_item_detail_payload(request.auth.user, entity, item_id))


@api.post(
    "/foods/label-captures",
    auth=mobile_bearer,
    response={200: FoodLabelCaptureEnvelope, 403: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def confirm_food_label_capture(request, payload: FoodLabelCaptureInput):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    capabilities = get_capabilities(request.auth.user)
    if capabilities is None or not capabilities.can_create_food():
        raise MobileAPIError(
            code="food_creation_not_entitled",
            message="The current account cannot create private foods.",
            status_code=403,
        )
    try:
        result = create_food_from_label_capture(
            user=request.auth.user,
            name=payload.name,
            protein_g=payload.protein_g,
            carbs_g=payload.carbs_g,
            fat_g=payload.fat_g,
            saturated_fat_g=payload.saturated_fat_g,
            sugar_g=payload.sugar_g,
            fiber_g=payload.fiber_g,
            sodium_mg=payload.sodium_mg,
            serving_size_g=payload.serving_size_g,
            declared_energy_kcal_per_100g=payload.declared_energy_kcal_per_100g,
            detected_basis=payload.detected_basis,
            ocr_engine=payload.ocr_engine,
            ocr_engine_version=payload.ocr_engine_version,
            field_confidence=payload.field_confidence,
            warnings=payload.warnings,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        raise _food_label_error(exc) from exc
    return _success(food_label_capture_payload(result))


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
                "items": [
                    str(row.get("name") or "")[:120]
                    for row in snapshot[:8]
                    if isinstance(row, dict)
                ],
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


@api.post("/ai/prepared-actions/{action_id}/commit", auth=mobile_bearer, response={200: AIPreparedActionResultEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope})
def commit_ai_prepared_action(request, action_id: str):
    _require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        action = commit_prepared_action(user=request.auth.user, public_id=action_id)
    except ValueError as exc:
        raise _prepared_action_error(exc) from exc
    return _success({"action_id": str(action.public_id), "status": action.status, "refresh_chat": True})


@api.post("/ai/prepared-actions/{action_id}/cancel", auth=mobile_bearer, response={200: AIPreparedActionResultEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope})
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
