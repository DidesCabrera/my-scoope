from __future__ import annotations

from zoneinfo import ZoneInfo

from django.db.models import Count
from django.utils import timezone

from notas.domain.models import CalendarizedDay, Program, ProgramCalendarization


def owned_programs_for_calendarization(user):
    return Program.objects.filter(created_by=user).annotate(
        calendarization_filled_days=Count("program_dailyplan")
    ).order_by("list_order", "-created_at", "-id")


def current_calendarization_for_user(user):
    return (
        ProgramCalendarization.objects.filter(
            user=user,
            status__in=ProgramCalendarization.CURRENT_STATUSES,
        )
        .prefetch_related("days")
        .first()
    )


def calendarization_history_for_user(user, *, limit=10):
    return ProgramCalendarization.objects.filter(user=user).exclude(
        status__in=ProgramCalendarization.CURRENT_STATUSES,
    )[:limit]


def calendarized_day_for_user(user, day_id):
    return CalendarizedDay.objects.select_related("calendarization").filter(
        id=day_id,
        calendarization__user=user,
    ).first()


def today_for_calendarization(calendarization, *, now=None):
    instant = now or timezone.now()
    return instant.astimezone(ZoneInfo(calendarization.timezone_name)).date()
