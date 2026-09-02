from __future__ import annotations

from ninja import Router

from mobile_api.api_support import calendarization_error, require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.schema_domains.calendarization import CalendarizedDayDetailEnvelope
from mobile_api.schema_domains.calendarization_edits import (
    CalendarizedMealHourInput,
    CalendarizedNameInput,
)
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors import calendarized_day_payload
from notas.application.services.commands.calendarization_commands import (
    rename_calendarized_day_plan,
    rename_calendarized_meal,
    update_calendarized_meal_hour,
)
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router()


def _updated_day_payload(request, day_id: int) -> dict:
    day = calendarized_day_payload(request.auth.user, day_id)
    if day is None:
        raise calendarization_error(ValueError("calendarized_day_not_found"))
    return success(day)


@router.get(
    "/program/days/{day_id}",
    operation_id="mobile_api_api_calendarized_day_detail",
    auth=mobile_bearer,
    response={200: CalendarizedDayDetailEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def calendarized_day_detail(request, day_id: int):
    return _updated_day_payload(request, day_id)


@router.patch(
    "/program/days/{day_id}",
    operation_id="mobile_api_api_calendarized_day_rename",
    auth=mobile_bearer,
    response={
        200: CalendarizedDayDetailEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def calendarized_day_rename(request, day_id: int, payload: CalendarizedNameInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        rename_calendarized_day_plan(user=request.auth.user, day_id=day_id, name=payload.name)
    except ValueError as exc:
        raise calendarization_error(exc) from exc
    return _updated_day_payload(request, day_id)


@router.patch(
    "/program/days/{day_id}/meals/{meal_snapshot_key}",
    operation_id="mobile_api_api_calendarized_meal_hour_update",
    auth=mobile_bearer,
    response={
        200: CalendarizedDayDetailEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def calendarized_meal_hour_update(request, day_id: int, meal_snapshot_key: str, payload: CalendarizedMealHourInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        update_calendarized_meal_hour(
            user=request.auth.user,
            day_id=day_id,
            meal_snapshot_key=meal_snapshot_key,
            hour=payload.hour,
        )
    except ValueError as exc:
        raise calendarization_error(exc) from exc
    return _updated_day_payload(request, day_id)


@router.patch(
    "/program/days/{day_id}/meals/{meal_snapshot_key}/name",
    operation_id="mobile_api_api_calendarized_meal_rename",
    auth=mobile_bearer,
    response={
        200: CalendarizedDayDetailEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def calendarized_meal_rename(request, day_id: int, meal_snapshot_key: str, payload: CalendarizedNameInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        rename_calendarized_meal(
            user=request.auth.user,
            day_id=day_id,
            meal_snapshot_key=meal_snapshot_key,
            name=payload.name,
        )
    except ValueError as exc:
        raise calendarization_error(exc) from exc
    return _updated_day_payload(request, day_id)
