from __future__ import annotations

from datetime import date

from notas.domain.models import (
    CalendarizationMeasurementContext,
    CalendarizationRevision,
    CalendarizedMealExecution,
)


def meal_execution_state_for_day(day) -> list[dict]:
    latest_by_key: dict[str, CalendarizedMealExecution] = {}
    events = day.meal_execution_events.all().order_by("created_at", "id")
    for event in events:
        latest_by_key[event.meal_snapshot_key] = event

    state = []
    for meal in (day.plan_snapshot or {}).get("meals", []):
        meal_key = meal.get("key") or ""
        event = latest_by_key.get(meal_key)
        status = "planned" if event is None or event.action == CalendarizedMealExecution.ACTION_RESET else event.action
        state.append(
            {
                "meal_key": meal_key,
                "status": status,
                "last_event_id": event.id if event else None,
                "recorded_at": event.created_at if event else None,
                "note": event.note if event and event.action != CalendarizedMealExecution.ACTION_RESET else "",
            }
        )
    return state


def calendarization_progress_summary(calendarization, *, period_start: date, period_end: date) -> dict:
    days = list(
        calendarization.days.filter(
            calendar_date__gte=period_start,
            calendar_date__lte=period_end,
        ).prefetch_related("meal_execution_events")
    )
    planned = completed = skipped = 0
    days_with_plan = 0
    for day in days:
        meals = (day.plan_snapshot or {}).get("meals", [])
        if day.plan_snapshot:
            days_with_plan += 1
        planned += len(meals)
        for item in meal_execution_state_for_day(day):
            if item["status"] == CalendarizedMealExecution.ACTION_COMPLETED:
                completed += 1
            elif item["status"] == CalendarizedMealExecution.ACTION_SKIPPED:
                skipped += 1

    unrecorded = max(planned - completed - skipped, 0)
    adherence_percent = round((completed / planned) * 100) if planned else 0
    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "days": len(days),
        "days_with_plan": days_with_plan,
        "planned_meals": planned,
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
