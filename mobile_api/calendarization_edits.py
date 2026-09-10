from __future__ import annotations

from mobile_api.api_support import calendarization_error
from mobile_api.errors import MobileAPIError
from mobile_api.selectors import library_item_detail_payload
from notas.application.services.calendarization.scheduling import local_date_for_timezone
from notas.application.services.commands.calendarization_execution_commands import (
    assign_dailyplan_to_calendarized_day,
)
from notas.domain.models import CalendarizedDay, DailyPlan, ProgramCalendarization


def _selection_context(*, user, day_id: int, dailyplan_id: int):
    day = (
        CalendarizedDay.objects.select_related("calendarization")
        .filter(pk=day_id, calendarization__user=user)
        .first()
    )
    if day is None:
        raise calendarization_error(ValueError("calendarized_day_not_found"))
    if day.calendarization.status not in ProgramCalendarization.CURRENT_STATUSES:
        raise calendarization_error(ValueError("calendarization_not_current"))
    if day.calendar_date <= local_date_for_timezone(day.calendarization.timezone_name):
        raise calendarization_error(ValueError("calendarization_revision_effective_date_invalid"))

    dailyplan = (
        DailyPlan.objects.filter(pk=dailyplan_id, created_by=user, is_draft=False)
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .first()
    )
    if dailyplan is None:
        raise MobileAPIError(
            "picker_selection_not_found",
            "El plan diario seleccionado no está disponible.",
            404,
        )
    return day, dailyplan


def preview_dailyplan_for_calendarized_day(*, user, day_id: int, dailyplan_id: int) -> dict:
    day, dailyplan = _selection_context(user=user, day_id=day_id, dailyplan_id=dailyplan_id)
    item = library_item_detail_payload(user, "daily-plans", dailyplan.id)
    result = {
        "id": item["id"],
        "entity": item["entity"],
        "name": item["name"],
        "nutrition": item["nutrition"],
        "indicators": item["indicators"],
        "panel": item["panel"],
    }
    replacements = [day.calendar_date.isoformat()] if day.plan_snapshot else []
    return {
        "selection": {
            "id": item["id"],
            "entity": item["entity"],
            "name": item["name"],
            "nutrition": item["nutrition"],
            "quantity": None,
            "hour": None,
        },
        "impacts": [],
        "result": result,
        "replacements": replacements,
        "confirmation_required": bool(replacements),
    }


def add_dailyplan_to_calendarized_day(
    *,
    user,
    day_id: int,
    dailyplan_id: int,
    idempotency_key: str,
    confirm_replacement: bool,
) -> dict:
    _selection_context(user=user, day_id=day_id, dailyplan_id=dailyplan_id)
    try:
        revision = assign_dailyplan_to_calendarized_day(
            user=user,
            day_id=day_id,
            dailyplan_id=dailyplan_id,
            idempotency_key=idempotency_key,
            confirm_replacement=confirm_replacement,
        )
    except ValueError as exc:
        raise calendarization_error(exc) from exc
    return {
        "message": "Plan diario asignado al programa activo.",
        "target_id": day_id,
        "created_id": revision.id,
    }
