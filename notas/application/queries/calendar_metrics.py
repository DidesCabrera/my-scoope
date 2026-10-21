from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db.models import Count, Max
from django.utils import timezone

from notas.application.queries.calendarization_execution_queries import (
    _meal_has_elapsed,
    meal_execution_state_for_day,
)
from notas.application.services.calendarization.scheduling import local_date_for_timezone
from notas.domain.models import CalendarizedDay, CalendarProgressPeriod


def calendar_progress_period_for_user(user) -> CalendarProgressPeriod | None:
    return CalendarProgressPeriod.objects.filter(user=user, ends_on__isnull=True).first()


def calendar_future_schedule_summary(user, *, today: date) -> dict:
    current_plans = (
        CalendarizedDay.objects.filter(
            user=user,
            assignment_state=CalendarizedDay.STATE_CURRENT,
            calendar_date__gte=today,
        )
        .exclude(plan_snapshot__isnull=True)
        .exclude(plan_snapshot={})
    )
    summary = current_plans.aggregate(future_plans_count=Count("id"), last_scheduled_date=Max("calendar_date"))
    return summary


def calendar_adherence_summary(
    user,
    *,
    period_start: date | None = None,
    period_end: date | None = None,
    now: datetime | None = None,
) -> dict:
    timezone_name = user.profile.timezone_name or "UTC"
    try:
        local_zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        local_zone = ZoneInfo("UTC")
    local_now = (now or timezone.now()).astimezone(local_zone)
    today = local_date_for_timezone(timezone_name, now=now)
    current_period = calendar_progress_period_for_user(user)
    first_day = (
        CalendarizedDay.objects.filter(
            user=user, assignment_state=CalendarizedDay.STATE_CURRENT, plan_snapshot__isnull=False
        )
        .exclude(plan_snapshot={})
        .order_by("calendar_date")
        .values_list("calendar_date", flat=True)
        .first()
    )
    start = period_start or (current_period.starts_on if current_period else first_day or today)
    end = min(period_end or today, today)
    planned_days_query = CalendarizedDay.objects.filter(
        user=user,
        assignment_state=CalendarizedDay.STATE_CURRENT,
        plan_snapshot__isnull=False,
        calendar_date__gte=start,
    ).exclude(plan_snapshot={})
    if period_end is not None:
        planned_days_query = planned_days_query.filter(calendar_date__lte=period_end)
    planned_snapshots = list(planned_days_query.values_list("plan_snapshot", flat=True))
    scheduled = sum(len(snapshot.get("meals", [])) for snapshot in planned_snapshots)
    days = list(
        CalendarizedDay.objects.filter(
            user=user,
            assignment_state=CalendarizedDay.STATE_CURRENT,
            plan_snapshot__isnull=False,
            calendar_date__gte=start,
            calendar_date__lte=end,
        ).exclude(plan_snapshot={}).prefetch_related("meal_execution_events").order_by("calendar_date")
    ) if start <= end else []
    elapsed = completed = skipped = 0
    for day in days:
        meals = (day.plan_snapshot or {}).get("meals", [])
        state = {item["meal_key"]: item["status"] for item in meal_execution_state_for_day(day)}
        for meal in meals:
            status = state.get(meal.get("key") or "", "planned")
            if not _meal_has_elapsed(day_date=day.calendar_date, meal=meal, status=status, local_now=local_now):
                continue
            elapsed += 1
            if status == "completed":
                completed += 1
            elif status == "skipped":
                skipped += 1
    return {
        "period_id": current_period.id if current_period and period_start is None else None,
        "period_start": start,
        "period_end": end,
        "days_with_plan": len(days),
        "scheduled_meals": scheduled,
        "elapsed_meals": elapsed,
        "completed_meals": completed,
        "skipped_meals": skipped,
        "unrecorded_meals": max(elapsed - completed - skipped, 0),
        "adherence_percent": round(completed / elapsed * 100) if elapsed else 0,
    }
