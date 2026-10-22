from django.db.models import Q

from notas.application.queries.calendarization_execution_queries import meal_execution_state_for_day
from notas.domain.models import CalendarizedDay, ProgramCalendarization


def current_dated_day(user, local_date):
    return (
        CalendarizedDay.objects.select_related("calendarization")
        .filter(
            Q(user=user) | Q(user__isnull=True, calendarization__user=user),
            calendar_date=local_date,
            assignment_state=CalendarizedDay.STATE_CURRENT,
        )
        .first()
    )


def standalone_today_payload(user, local_date, day, *, calendarization_supplied, calendarization_id, snapshot_formatter):
    if day is None or not (
        day.calendarization is None
        or day.calendarization.status not in ProgramCalendarization.CURRENT_STATUSES
        or (calendarization_supplied and day.calendarization_id != calendarization_id)
    ):
        return None
    return {
        "local_date": local_date,
        "calendarization": None,
        "day_id": day.id,
        "source_dailyplan_id": day.source_dailyplan_id,
        "has_plan": day.has_plan,
        "plan_snapshot": snapshot_formatter(user, day.plan_snapshot) if day.has_plan else None,
        "meal_execution": meal_execution_state_for_day(day) if day.has_plan else [],
        "adherence": None,
        "measurements": None,
        "reminders": None,
        "pending_revision": None,
        "pinned_plan": None,
    }
