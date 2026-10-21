from __future__ import annotations

from datetime import date

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from notas.application.queries.calendar_foods import calendar_foods_for_period
from notas.application.services.calendarization.scheduling import local_date_for_timezone
from notas.domain.models import CalendarCommitment


@transaction.atomic
def register_calendar_commitments(
    *, user: User, kind: str, dates: list[date], note: str = "",
    food_period_start: date | None = None, food_period_end: date | None = None,
) -> list[CalendarCommitment]:
    if kind not in {choice for choice, _ in CalendarCommitment.KIND_CHOICES}:
        raise ValueError("calendar_commitment_kind_invalid")
    if not dates or len(dates) > 62 or len(set(dates)) != len(dates):
        raise ValueError("calendar_commitment_dates_invalid")
    today = local_date_for_timezone(user.profile.timezone_name or "UTC")
    if any(day < today for day in dates):
        raise ValueError("calendar_commitment_date_in_past")
    clean_note = note.strip()
    if len(clean_note) > 500:
        raise ValueError("calendar_commitment_note_too_long")
    if (food_period_start is None) != (food_period_end is None):
        raise ValueError("calendar_food_period_incomplete")
    if kind != CalendarCommitment.KIND_SHOPPING and food_period_start is not None:
        raise ValueError("calendar_food_period_wrong_kind")

    User.objects.select_for_update().get(pk=user.pk)
    if CalendarCommitment.objects.filter(user=user, kind=kind, calendar_date__in=dates).exists():
        raise ValueError("calendar_commitment_already_exists")
    period = (
        calendar_foods_for_period(user, start_date=food_period_start, end_date=food_period_end)
        if food_period_start is not None and food_period_end is not None else None
    )
    commitments = [
        CalendarCommitment(
            user=user, kind=kind, calendar_date=day, note=clean_note,
            food_period_start=food_period_start, food_period_end=food_period_end,
            food_plans_count=period["plans_count"] if period else 0,
            foods_snapshot=period["foods_aggregation_table"] if period else [],
        )
        for day in sorted(dates)
    ]
    try:
        return CalendarCommitment.objects.bulk_create(commitments)
    except IntegrityError as exc:
        raise ValueError("calendar_commitment_already_exists") from exc
