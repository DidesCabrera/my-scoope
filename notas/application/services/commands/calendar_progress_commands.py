from __future__ import annotations

from datetime import date, datetime, timedelta

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from notas.application.queries.calendar_metrics import calendar_progress_period_for_user
from notas.application.services.calendarization.scheduling import local_date_for_timezone
from notas.domain.models import CalendarizedDay, CalendarProgressPeriod


@transaction.atomic
def start_new_calendar_progress_period(*, user, now: datetime | None = None) -> CalendarProgressPeriod:
    """Start a new visible metric period; historical evidence remains unchanged."""
    current_time = now or timezone.now()
    today = local_date_for_timezone(user.profile.timezone_name or "UTC", now=current_time)
    User.objects.select_for_update().get(pk=user.pk)
    current = calendar_progress_period_for_user(user)
    if current is None:
        first_date = (
            CalendarizedDay.objects.filter(
                user=user, assignment_state=CalendarizedDay.STATE_CURRENT, plan_snapshot__isnull=False
            )
            .order_by("calendar_date")
            .values_list("calendar_date", flat=True)
            .first()
        )
        if first_date is None or first_date >= today:
            raise ValueError("calendar_progress_no_prior_period")
        current = CalendarProgressPeriod.objects.create(user=user, starts_on=first_date)
    if current.starts_on >= today:
        raise ValueError("calendar_progress_period_already_started_today")
    current.ends_on = today - timedelta(days=1)
    current.closed_at = current_time
    current.save(update_fields=["ends_on", "closed_at"])
    return CalendarProgressPeriod.objects.create(user=user, starts_on=today)


@transaction.atomic
def adjust_calendar_progress_period_start(
    *, user, starts_on: date, now: datetime | None = None
) -> CalendarProgressPeriod:
    """Select a reporting range while retaining earlier period choices and execution evidence."""
    current_time = now or timezone.now()
    today = local_date_for_timezone(user.profile.timezone_name or "UTC", now=current_time)
    if starts_on > today:
        raise ValueError("calendar_progress_start_in_future")
    User.objects.select_for_update().get(pk=user.pk)
    current = calendar_progress_period_for_user(user)
    if current is not None:
        if current.starts_on == starts_on:
            return current
        current.ends_on = max(today - timedelta(days=1), current.starts_on)
        current.closed_at = current_time
        current.save(update_fields=["ends_on", "closed_at"])
    return CalendarProgressPeriod.objects.create(user=user, starts_on=starts_on)
