from __future__ import annotations

from ninja import Router

from mobile_api.api_support import calendarization_error, require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.calendarization import (
    ActiveProgramEnvelope,
    ApplePushRegistrationEnvelope,
    ApplePushRegistrationInput,
    CalendarizationActivationEnvelope,
    CalendarizationActivationInput,
    CalendarizationHistoryEnvelope,
    CalendarizationReviewEnvelope,
    CalendarizationReviewInput,
    CalendarizationReviewListEnvelope,
    CalendarizedDayDetailEnvelope,
    MealCheckInInput,
    ReminderSettingsEnvelope,
    ReminderSettingsInput,
    RevisionDecisionInput,
    RevisionEnvelope,
    RevisionListEnvelope,
    TodayEnvelope,
    WeightCreateInput,
    WeightEnvelope,
    WeightListEnvelope,
)
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors import (
    active_program_payload,
    calendarization_history_payload,
    calendarized_day_payload,
    reminder_settings_payload,
    review_payload,
    revision_payload,
    today_payload,
)
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
from notas.application.services.notifications.apple_push import apns_is_configured
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE
from notas.domain.models import (
    CalendarizationReview,
    CalendarizationRevision,
    Program,
    ProgramCalendarization,
    WeightLog,
)

router = Router()


@router.get(
    "/program/active",
    operation_id="mobile_api_api_active_program",
    auth=mobile_bearer,
    response={200: ActiveProgramEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def active_program(request):
    return success(active_program_payload(request.auth.user))


@router.post(
    "/program/calendarizations",
    operation_id="mobile_api_api_activate_calendarization",
    auth=mobile_bearer,
    response={
        200: CalendarizationActivationEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def activate_calendarization(request, payload: CalendarizationActivationInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    program = Program.objects.filter(pk=payload.program_id, created_by=request.auth.user).first()
    if program is None:
        raise calendarization_error(ValueError("calendarization_program_not_owned"))
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
        error = calendarization_error(exc)
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
    return success(response)


@router.get(
    "/program/calendarizations/history",
    operation_id="mobile_api_api_calendarization_history",
    auth=mobile_bearer,
    response={200: CalendarizationHistoryEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def calendarization_history(request, limit: int = 20):
    return success(calendarization_history_payload(request.auth.user, limit=limit))


@router.get(
    "/program/days/{day_id}",
    operation_id="mobile_api_api_calendarized_day_detail",
    auth=mobile_bearer,
    response={200: CalendarizedDayDetailEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def calendarized_day_detail(request, day_id: int):
    day = calendarized_day_payload(request.auth.user, day_id)
    if day is None:
        raise calendarization_error(ValueError("calendarized_day_not_found"))
    return success(day)


def _calendarization_state_action(request, calendarization_id: int, command):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        command(user=request.auth.user, calendarization_id=calendarization_id)
    except ValueError as exc:
        raise calendarization_error(exc) from exc
    return success(active_program_payload(request.auth.user))


@router.post(
    "/program/calendarizations/{calendarization_id}/pause",
    operation_id="mobile_api_api_pause_active_calendarization",
    auth=mobile_bearer,
    response={
        200: ActiveProgramEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def pause_active_calendarization(request, calendarization_id: int):
    return _calendarization_state_action(request, calendarization_id, pause_calendarization)


@router.post(
    "/program/calendarizations/{calendarization_id}/resume",
    operation_id="mobile_api_api_resume_active_calendarization",
    auth=mobile_bearer,
    response={
        200: ActiveProgramEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def resume_active_calendarization(request, calendarization_id: int):
    return _calendarization_state_action(request, calendarization_id, resume_calendarization)


@router.post(
    "/program/calendarizations/{calendarization_id}/cancel",
    operation_id="mobile_api_api_cancel_active_calendarization",
    auth=mobile_bearer,
    response={
        200: ActiveProgramEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def cancel_active_calendarization(request, calendarization_id: int):
    return _calendarization_state_action(request, calendarization_id, cancel_calendarization)


@router.get(
    "/today",
    operation_id="mobile_api_api_today",
    auth=mobile_bearer,
    response={200: TodayEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def today(request):
    return success(today_payload(request.auth.user))


@router.post(
    "/days/{day_id}/meals/{meal_snapshot_key}/check-ins",
    operation_id="mobile_api_api_meal_check_in",
    auth=mobile_bearer,
    response={200: TodayEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def meal_check_in(request, day_id: int, meal_snapshot_key: str, payload: MealCheckInInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
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
        raise calendarization_error(exc) from exc
    return success(today_payload(request.auth.user))


@router.put(
    "/program/active/reminders",
    operation_id="mobile_api_api_update_active_program_reminders",
    auth=mobile_bearer,
    response={200: ReminderSettingsEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def update_active_program_reminders(request, payload: ReminderSettingsInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    calendarization = ProgramCalendarization.objects.filter(
        user=request.auth.user,
        status__in=ProgramCalendarization.CURRENT_STATUSES,
    ).first()
    if calendarization is None:
        raise calendarization_error(ValueError("calendarization_not_found"))
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
        raise calendarization_error(exc) from exc
    return success(reminder_settings_payload(calendarization))


@router.put(
    "/notifications/apple/device",
    operation_id="mobile_api_api_register_apple_notification_device",
    auth=mobile_bearer,
    response={200: ApplePushRegistrationEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def register_apple_notification_device(request, payload: ApplePushRegistrationInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
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
    return success(
        {
            "delivery_mode": "apns" if apns_is_configured() else "local",
            "token_fingerprint": subscription.token_fingerprint,
            "environment": subscription.environment,
            "is_active": subscription.is_active,
        }
    )


@router.get(
    "/program/reviews",
    operation_id="mobile_api_api_program_reviews",
    auth=mobile_bearer,
    response={200: CalendarizationReviewListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def program_reviews(request, limit: int = 12):
    items = CalendarizationReview.objects.filter(calendarization__user=request.auth.user).order_by(
        "-period_end", "-created_at", "-id"
    )[: min(max(limit, 1), 50)]
    payload = [review_payload(item) for item in items]
    return success({"items": payload, "count": len(payload)})


@router.post(
    "/program/reviews",
    operation_id="mobile_api_api_create_program_review",
    auth=mobile_bearer,
    response={
        200: CalendarizationReviewEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def create_program_review(request, payload: CalendarizationReviewInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
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
        raise calendarization_error(exc) from exc
    return success(review_payload(review))


@router.get(
    "/program/revisions",
    operation_id="mobile_api_api_program_revisions",
    auth=mobile_bearer,
    response={200: RevisionListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def program_revisions(request, limit: int = 12):
    revisions = CalendarizationRevision.objects.filter(calendarization__user=request.auth.user).order_by(
        "-created_at", "-id"
    )[: min(max(limit, 1), 50)]
    payload = [revision_payload(item) for item in revisions]
    return success({"items": payload, "count": len(payload)})


@router.post(
    "/program/revisions/{revision_id}/decision",
    operation_id="mobile_api_api_decide_program_revision",
    auth=mobile_bearer,
    response={200: RevisionEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def decide_program_revision(request, revision_id: int, payload: RevisionDecisionInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        revision = decide_calendarization_revision(
            user=request.auth.user,
            revision_id=revision_id,
            decision=payload.decision,
        )
    except ValueError as exc:
        raise calendarization_error(exc) from exc
    return success(revision_payload(revision))


@router.get(
    "/weights",
    operation_id="mobile_api_api_weights",
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
    return success({"items": items, "count": len(items)})


@router.post(
    "/weights",
    operation_id="mobile_api_api_create_weight",
    auth=mobile_bearer,
    response={200: WeightEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def create_weight(request, payload: WeightCreateInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    item, context = record_calendarized_weight(
        user=request.auth.user,
        weight_kg=payload.weight_kg,
        measured_on=payload.measured_on,
    )
    return success(
        {
            "id": item.id,
            "measured_on": item.date,
            "weight_kg": item.weight_kg,
            "source": item.source,
            "created_at": item.created_at,
            "calendarization_id": context.calendarization_id if context else None,
        }
    )
