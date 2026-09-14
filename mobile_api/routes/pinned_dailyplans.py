from ninja import Router

from mobile_api.api_support import pinned_dailyplan_error, require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.schema_domains.calendarization import MealCheckInInput
from mobile_api.schema_domains.today import PinnedDailyPlanInput, TodayEnvelope
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors import local_date_for_user, today_payload
from notas.application.queries.calendarization_queries import current_calendarization_for_user
from notas.application.services.commands.pinned_dailyplan_commands import (
    create_and_pin_empty_dailyplan,
    pin_dailyplan,
    record_pinned_meal_execution,
    unpin_dailyplan,
)
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router()


def _require_no_current_calendarization(user):
    if current_calendarization_for_user(user) is not None:
        raise pinned_dailyplan_error(ValueError("pinned_dailyplan_active_calendarization"))


@router.post(
    "/today/pinned-plan",
    operation_id="mobile_api_api_create_and_pin_today_dailyplan",
    auth=mobile_bearer,
    response={200: TodayEnvelope, 403: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def create_and_pin_today_dailyplan(request):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _require_no_current_calendarization(request.auth.user)
    create_and_pin_empty_dailyplan(user=request.auth.user, local_date=local_date_for_user(request.auth.user))
    return success(today_payload(request.auth.user))


@router.put(
    "/today/pinned-plan",
    operation_id="mobile_api_api_pin_today_dailyplan",
    auth=mobile_bearer,
    response={200: TodayEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def pin_today_dailyplan(request, payload: PinnedDailyPlanInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _require_no_current_calendarization(request.auth.user)
    try:
        pin_dailyplan(user=request.auth.user, dailyplan_id=payload.dailyplan_id)
    except ValueError as exc:
        raise pinned_dailyplan_error(exc) from exc
    return success(today_payload(request.auth.user))


@router.delete(
    "/today/pinned-plan",
    operation_id="mobile_api_api_unpin_today_dailyplan",
    auth=mobile_bearer,
    response={200: TodayEnvelope, 403: ErrorEnvelope},
)
def unpin_today_dailyplan(request):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    unpin_dailyplan(user=request.auth.user)
    return success(today_payload(request.auth.user))


@router.post(
    "/today/pinned-plan/meals/{meal_key}/check-ins",
    operation_id="mobile_api_api_pinned_dailyplan_meal_check_in",
    auth=mobile_bearer,
    response={200: TodayEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def pinned_dailyplan_meal_check_in(request, meal_key: str, payload: MealCheckInInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _require_no_current_calendarization(request.auth.user)
    try:
        record_pinned_meal_execution(
            user=request.auth.user,
            local_date=local_date_for_user(request.auth.user),
            meal_key=meal_key,
            action=payload.action,
            idempotency_key=payload.idempotency_key,
            note=payload.note,
            food_key=payload.food_snapshot_key,
        )
    except ValueError as exc:
        raise pinned_dailyplan_error(exc) from exc
    return success(today_payload(request.auth.user))
