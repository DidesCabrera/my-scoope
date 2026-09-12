from __future__ import annotations

from ninja import Router

from mobile_api.api_support import calendarization_error, require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.calendarization_edits import (
    add_dailyplan_to_calendarized_day,
    preview_dailyplan_for_calendarized_day,
)
from mobile_api.calendarized_composition import (
    commit_food_to_calendarized_meal,
    commit_meal_to_calendarized_day,
    preview_food_for_calendarized_meal,
    preview_meal_for_calendarized_day,
)
from mobile_api.schema_domains.calendarization import CalendarizedDayDetailEnvelope
from mobile_api.schema_domains.calendarization_edits import (
    CalendarizedDayPlanCommitInput,
    CalendarizedDayPlanPreviewInput,
    CalendarizedFoodPickerInput,
    CalendarizedMealHourInput,
    CalendarizedMealPickerInput,
    CalendarizedNameInput,
)
from mobile_api.schema_domains.composition import PickerCommitEnvelope
from mobile_api.schema_domains.composition_preview import PickerPreviewEnvelope
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


@router.post(
    "/program/days/{day_id}/daily-plan-picker/preview",
    operation_id="mobile_api_api_calendarized_day_dailyplan_picker_preview",
    auth=mobile_bearer,
    response={
        200: PickerPreviewEnvelope,
        401: ErrorEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def calendarized_day_dailyplan_picker_preview(
    request,
    day_id: int,
    payload: CalendarizedDayPlanPreviewInput,
):
    return success(
        preview_dailyplan_for_calendarized_day(
            user=request.auth.user,
            day_id=day_id,
            dailyplan_id=payload.dailyplan_id,
        )
    )


@router.post(
    "/program/days/{day_id}/daily-plan-picker/commit",
    operation_id="mobile_api_api_calendarized_day_dailyplan_picker_commit",
    auth=mobile_bearer,
    response={
        200: PickerCommitEnvelope,
        401: ErrorEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def calendarized_day_dailyplan_picker_commit(
    request,
    day_id: int,
    payload: CalendarizedDayPlanCommitInput,
):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        add_dailyplan_to_calendarized_day(
            user=request.auth.user,
            day_id=day_id,
            dailyplan_id=payload.dailyplan_id,
            idempotency_key=payload.idempotency_key,
            confirm_replacement=payload.confirm_replacement,
        )
    )


@router.post(
    "/program/days/{day_id}/meal-picker/preview",
    operation_id="mobile_api_api_calendarized_day_meal_picker_preview",
    auth=mobile_bearer,
    response={200: PickerPreviewEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def calendarized_day_meal_picker_preview(request, day_id: int, payload: CalendarizedMealPickerInput):
    return success(
        preview_meal_for_calendarized_day(
            user=request.auth.user,
            day_id=day_id,
            meal_id=payload.meal_id,
            hour=payload.hour,
            note=payload.note,
        )
    )


@router.post(
    "/program/days/{day_id}/meal-picker/commit",
    operation_id="mobile_api_api_calendarized_day_meal_picker_commit",
    auth=mobile_bearer,
    response={200: PickerCommitEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def calendarized_day_meal_picker_commit(request, day_id: int, payload: CalendarizedMealPickerInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        commit_meal_to_calendarized_day(
            user=request.auth.user,
            day_id=day_id,
            meal_id=payload.meal_id,
            hour=payload.hour,
            note=payload.note,
        )
    )


@router.post(
    "/program/days/{day_id}/meals/{meal_snapshot_key}/food-picker/preview",
    operation_id="mobile_api_api_calendarized_meal_food_picker_preview",
    auth=mobile_bearer,
    response={200: PickerPreviewEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def calendarized_meal_food_picker_preview(
    request, day_id: int, meal_snapshot_key: str, payload: CalendarizedFoodPickerInput
):
    return success(
        preview_food_for_calendarized_meal(
            user=request.auth.user,
            day_id=day_id,
            meal_snapshot_key=meal_snapshot_key,
            food_id=payload.food_id,
            quantity=payload.quantity,
        )
    )


@router.post(
    "/program/days/{day_id}/meals/{meal_snapshot_key}/food-picker/commit",
    operation_id="mobile_api_api_calendarized_meal_food_picker_commit",
    auth=mobile_bearer,
    response={200: PickerCommitEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def calendarized_meal_food_picker_commit(
    request, day_id: int, meal_snapshot_key: str, payload: CalendarizedFoodPickerInput
):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        commit_food_to_calendarized_meal(
            user=request.auth.user,
            day_id=day_id,
            meal_snapshot_key=meal_snapshot_key,
            food_id=payload.food_id,
            quantity=payload.quantity,
        )
    )


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
