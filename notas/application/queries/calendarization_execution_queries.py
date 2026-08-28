from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from notas.domain.models import (
    CalendarizationMeasurementContext,
    CalendarizationRevision,
    CalendarizedMealExecution,
)


def meal_execution_state_for_day(day) -> list[dict]:
    latest_status_by_key: dict[str, CalendarizedMealExecution] = {}
    latest_note_by_key: dict[str, CalendarizedMealExecution] = {}
    events = day.meal_execution_events.all().order_by("created_at", "id")
    for event in events:
        if event.action == CalendarizedMealExecution.ACTION_NOTE:
            latest_note_by_key[event.meal_snapshot_key] = event
            continue
        latest_status_by_key[event.meal_snapshot_key] = event
        if event.note:
            latest_note_by_key[event.meal_snapshot_key] = event

    state = []
    for meal in (day.plan_snapshot or {}).get("meals", []):
        meal_key = meal.get("key") or ""
        status_event = latest_status_by_key.get(meal_key)
        note_event = latest_note_by_key.get(meal_key)
        status = "planned" if status_event is None or status_event.action == CalendarizedMealExecution.ACTION_RESET else status_event.action
        state.append(
            {
                "meal_key": meal_key,
                "status": status,
                "last_event_id": status_event.id if status_event else None,
                "recorded_at": status_event.created_at if status_event else None,
                "note": note_event.note if note_event else "",
            }
        )
    return state


def _calendarization_local_now(calendarization, now: datetime | None) -> datetime:
    try:
        local_timezone = ZoneInfo(calendarization.timezone_name)
    except ZoneInfoNotFoundError:
        local_timezone = ZoneInfo("UTC")
    return (now or timezone.now()).astimezone(local_timezone)


def _meal_has_elapsed(*, day_date: date, meal: dict, status: str, local_now: datetime) -> bool:
    if status in {CalendarizedMealExecution.ACTION_COMPLETED, CalendarizedMealExecution.ACTION_SKIPPED}:
        return True
    if day_date < local_now.date():
        return True
    if day_date > local_now.date():
        return False
    meal_hour = meal.get("hour")
    if not isinstance(meal_hour, str) or not meal_hour.strip():
        return False
    try:
        scheduled_time = time.fromisoformat(meal_hour.strip())
    except ValueError:
        return False
    return scheduled_time <= local_now.time().replace(tzinfo=None)


def calendarization_progress_summary(calendarization, *, period_start: date, period_end: date, now: datetime | None = None) -> dict:
    days = list(
        calendarization.days.filter(
            calendar_date__gte=period_start,
            calendar_date__lte=period_end,
        ).prefetch_related("meal_execution_events")
    )
    scheduled = elapsed = completed = skipped = 0
    days_with_plan = 0
    local_now = _calendarization_local_now(calendarization, now)
    for day in days:
        meals = (day.plan_snapshot or {}).get("meals", [])
        if day.plan_snapshot:
            days_with_plan += 1
        scheduled += len(meals)
        state_by_key = {item["meal_key"]: item for item in meal_execution_state_for_day(day)}
        for meal in meals:
            status = state_by_key.get(meal.get("key") or "", {}).get("status", "planned")
            if not _meal_has_elapsed(day_date=day.calendar_date, meal=meal, status=status, local_now=local_now):
                continue
            elapsed += 1
            if status == CalendarizedMealExecution.ACTION_COMPLETED:
                completed += 1
            elif status == CalendarizedMealExecution.ACTION_SKIPPED:
                skipped += 1

    unrecorded = max(elapsed - completed - skipped, 0)
    adherence_percent = round((completed / elapsed) * 100) if elapsed else 0
    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "days": len(days),
        "days_with_plan": days_with_plan,
        "scheduled_meals": scheduled,
        "elapsed_meals": elapsed,
        "planned_meals": elapsed,
        "completed_meals": completed,
        "skipped_meals": skipped,
        "unrecorded_meals": unrecorded,
        "adherence_percent": adherence_percent,
    }


def calendarization_measurement_summary(calendarization, *, period_start: date | None = None, period_end: date | None = None) -> dict:
    queryset = CalendarizationMeasurementContext.objects.filter(
        calendarization=calendarization,
    ).select_related("weight_log")
    if period_start is not None:
        queryset = queryset.filter(weight_log__date__gte=period_start)
    if period_end is not None:
        queryset = queryset.filter(weight_log__date__lte=period_end)
    contexts = list(queryset.order_by("weight_log__date", "weight_log__created_at", "id"))
    items = [
        {
            "weight_log_id": context.weight_log_id,
            "measured_on": context.weight_log.date.isoformat(),
            "weight_kg": context.weight_log.weight_kg,
        }
        for context in contexts
    ]
    first = items[0]["weight_kg"] if items else None
    latest = items[-1]["weight_kg"] if items else None
    return {
        "items": items,
        "count": len(items),
        "first_weight_kg": first,
        "latest_weight_kg": latest,
        "change_kg": round(latest - first, 2) if first is not None and latest is not None else None,
    }


def pending_revision_for_calendarization(calendarization) -> CalendarizationRevision | None:
    return (
        calendarization.revisions.filter(status=CalendarizationRevision.STATUS_PENDING)
        .select_related("review")
        .order_by("created_at", "id")
        .first()
    )
