from datetime import date, timedelta

from django.db.models import Count
from ninja import Router

from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.calendar import (
    CalendarAssignmentInput,
    CalendarDayDetailEnvelope,
    CalendarDayHistoryEnvelope,
    CalendarDraftInput,
    CalendarMoveInput,
    CalendarOverviewEnvelope,
    CalendarProgressEnvelope,
)
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors import _calendarized_snapshot_with_meal_links, local_date_for_user
from notas.application.queries.calendar_metrics import calendar_adherence_summary, calendar_future_schedule_summary
from notas.application.queries.calendarization_execution_queries import meal_execution_state_for_day
from notas.application.services.commands.calendar_day_commands import (
    assign_dailyplan_to_calendar_date,
    create_and_assign_draft_to_calendar_date,
    move_calendar_date_plan,
    remove_calendar_date_plan,
)
from notas.application.services.commands.calendar_progress_commands import start_new_calendar_progress_period
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE
from notas.domain.models import CalendarizedDay

router = Router()


def _error(exc: ValueError) -> MobileAPIError:
    code = str(exc)
    return MobileAPIError(
        code=code,
        message="No pudimos actualizar el calendario.",
        status_code=(
            404 if code in {"calendar_dailyplan_not_owned", "calendar_day_not_found"}
            else 409 if code in {
                "calendar_replacement_confirmation_required", "calendar_day_has_execution",
                "calendar_assignment_key_conflict", "calendar_date_in_past",
                "calendar_move_program_day_unsupported",
                "calendar_progress_no_prior_period", "calendar_progress_period_already_started_today",
            }
            else 422
        ),
    )


def _day_payload(user, day: CalendarizedDay) -> dict:
    origin = day.origin_calendarization or day.calendarization
    return {
        "id": day.id,
        "calendar_date": day.calendar_date,
        "has_plan": day.has_plan,
        "plan_name": (day.plan_snapshot or {}).get("name", ""),
        "source_kind": day.source_kind,
        "source_program_name": origin.program_name_snapshot if origin else None,
        "has_execution": day.meal_execution_events.exists(),
        "plan_snapshot": _calendarized_snapshot_with_meal_links(user, day.plan_snapshot),
        "meal_execution": meal_execution_state_for_day(day),
    }


@router.get(
    "/calendar",
    operation_id="mobile_api_api_calendar_overview",
    auth=mobile_bearer,
    response={200: CalendarOverviewEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def calendar_overview(request, start_date: date | None = None, days: int = 28):
    if not 1 <= days <= 42:
        raise MobileAPIError(code="calendar_range_invalid", message="El rango debe tener entre 1 y 42 días.", status_code=422)
    local_today = local_date_for_user(request.auth.user)
    first = start_date or (local_today - timedelta(days=local_today.weekday()))
    last = first + timedelta(days=days - 1)
    rows = CalendarizedDay.objects.filter(
        user=request.auth.user,
        assignment_state=CalendarizedDay.STATE_CURRENT,
        calendar_date__range=(first, last),
    ).select_related("calendarization", "origin_calendarization").prefetch_related("meal_execution_events").order_by("calendar_date")
    by_date = {row.calendar_date: row for row in rows}
    items = []
    for offset in range(days):
        current_date = first + timedelta(days=offset)
        day = by_date.get(current_date)
        items.append({
            "id": day.id if day else None,
            "calendar_date": current_date,
            "has_plan": bool(day and day.has_plan),
            "plan_name": (day.plan_snapshot or {}).get("name", "") if day and day.has_plan else "",
            "source_kind": day.source_kind if day else None,
            "source_program_name": (day.origin_calendarization or day.calendarization).program_name_snapshot if day and (day.origin_calendarization or day.calendarization) else None,
            "has_execution": bool(day.meal_execution_events.all()) if day else False,
        })
    return success({
        "local_date": local_today,
        "start_date": first,
        "end_date": last,
        "days": items,
        **calendar_future_schedule_summary(request.auth.user, today=local_today),
    })


@router.get(
    "/calendar/progress",
    operation_id="mobile_api_api_calendar_progress",
    auth=mobile_bearer,
    response={200: CalendarProgressEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def calendar_progress(request):
    return success(calendar_adherence_summary(request.auth.user))


@router.post(
    "/calendar/progress/periods",
    operation_id="mobile_api_api_start_calendar_progress_period",
    auth=mobile_bearer,
    response={200: CalendarProgressEnvelope, 403: ErrorEnvelope, 409: ErrorEnvelope},
)
def start_calendar_progress_period(request):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        start_new_calendar_progress_period(user=request.auth.user)
    except ValueError as exc:
        raise _error(exc) from exc
    return success(calendar_adherence_summary(request.auth.user))


@router.get(
    "/calendar/days/{local_date}",
    operation_id="mobile_api_api_calendar_day",
    auth=mobile_bearer,
    response={200: CalendarDayDetailEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def calendar_day(request, local_date: date):
    day = CalendarizedDay.objects.select_related("calendarization", "origin_calendarization").filter(
        user=request.auth.user, calendar_date=local_date, assignment_state=CalendarizedDay.STATE_CURRENT
    ).first()
    if day is None:
        return success({
            "id": None,
            "calendar_date": local_date,
            "has_plan": False,
            "plan_name": "",
            "source_kind": None,
            "source_program_name": None,
            "has_execution": False,
            "plan_snapshot": None,
            "meal_execution": [],
        })
    return success(_day_payload(request.auth.user, day))


@router.get(
    "/calendar/days/{local_date}/history",
    operation_id="mobile_api_api_calendar_day_history",
    auth=mobile_bearer,
    response={200: CalendarDayHistoryEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def calendar_day_history(request, local_date: date):
    rows = CalendarizedDay.objects.filter(
        user=request.auth.user, calendar_date=local_date,
    ).select_related("calendarization", "origin_calendarization").annotate(
        execution_count=Count("meal_execution_events"),
    ).order_by("created_at", "id")
    return success({
        "calendar_date": local_date,
        "items": [{
            "id": day.id,
            "calendar_date": day.calendar_date,
            "plan_name": (day.plan_snapshot or {}).get("name", ""),
            "source_kind": day.source_kind,
            "source_program_name": (day.origin_calendarization or day.calendarization).program_name_snapshot if (day.origin_calendarization or day.calendarization) else None,
            "assignment_state": day.assignment_state,
            "created_at": day.created_at.isoformat(),
            "state_changed_at": day.state_changed_at.isoformat() if day.state_changed_at else None,
            "change_reason": day.change_reason,
            "superseded_by_id": day.superseded_by_id,
            "execution_events": day.execution_count,
        } for day in rows],
    })


@router.put(
    "/calendar/days/{local_date}/plan",
    operation_id="mobile_api_api_assign_calendar_day_plan",
    auth=mobile_bearer,
    response={200: CalendarDayDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def assign_calendar_day_plan(request, local_date: date, payload: CalendarAssignmentInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        day = assign_dailyplan_to_calendar_date(
            user=request.auth.user,
            dailyplan_id=payload.dailyplan_id,
            local_date=local_date,
            assignment_key=payload.assignment_key,
            replace_existing=payload.replace_existing,
        )
    except ValueError as exc:
        raise _error(exc) from exc
    return success(_day_payload(request.auth.user, day))


@router.post(
    "/calendar/days/{local_date}/plan/draft",
    operation_id="mobile_api_api_create_calendar_day_draft",
    auth=mobile_bearer,
    response={200: CalendarDayDetailEnvelope, 403: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def create_calendar_day_draft(request, local_date: date, payload: CalendarDraftInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        day = create_and_assign_draft_to_calendar_date(
            user=request.auth.user, local_date=local_date, assignment_key=payload.assignment_key,
        )
    except ValueError as exc:
        raise _error(exc) from exc
    return success(_day_payload(request.auth.user, day))


@router.delete(
    "/calendar/days/{local_date}/plan",
    operation_id="mobile_api_api_remove_calendar_day_plan",
    auth=mobile_bearer,
    response={200: CalendarDayDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def remove_calendar_day_plan(request, local_date: date):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        remove_calendar_date_plan(user=request.auth.user, local_date=local_date)
    except ValueError as exc:
        raise _error(exc) from exc
    return success({
        "id": None,
        "calendar_date": local_date,
        "has_plan": False,
        "plan_name": "",
        "source_kind": None,
        "source_program_name": None,
        "has_execution": False,
        "plan_snapshot": None,
        "meal_execution": [],
    })


@router.post(
    "/calendar/days/{local_date}/move",
    operation_id="mobile_api_api_move_calendar_day_plan",
    auth=mobile_bearer,
    response={200: CalendarDayDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def move_calendar_day_plan(request, local_date: date, payload: CalendarMoveInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        day = move_calendar_date_plan(
            user=request.auth.user,
            source_date=local_date,
            target_date=payload.target_date,
            assignment_key=payload.assignment_key,
            replace_existing=payload.replace_existing,
        )
    except ValueError as exc:
        raise _error(exc) from exc
    return success(_day_payload(request.auth.user, day))
