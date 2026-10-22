from __future__ import annotations

from copy import deepcopy
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
    food_attachments: list[tuple[date, date, date]] | None = None,
    notes_by_date: dict[date, str] | None = None,
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
    day_notes = {day: value.strip() for day, value in (notes_by_date or {}).items()}
    if not set(day_notes).issubset(dates):
        raise ValueError("calendar_commitment_note_dates_invalid")
    if any(len(value) > 500 for value in day_notes.values()):
        raise ValueError("calendar_commitment_note_too_long")
    if (food_period_start is None) != (food_period_end is None):
        raise ValueError("calendar_food_period_incomplete")
    attachments = list(food_attachments or [])
    if food_period_start is not None:
        if len(dates) != 1 or attachments:
            raise ValueError("calendar_food_period_multiple_dates")
        attachments.append((dates[0], food_period_start, food_period_end))
    if kind not in {CalendarCommitment.KIND_SHOPPING, CalendarCommitment.KIND_COOKING} and attachments:
        raise ValueError("calendar_food_period_wrong_kind")
    attachment_dates = [day for day, _, _ in attachments]
    if len(set(attachment_dates)) != len(attachment_dates) or not set(attachment_dates).issubset(dates):
        raise ValueError("calendar_food_attachment_dates_invalid")

    User.objects.select_for_update().get(pk=user.pk)
    if CalendarCommitment.objects.filter(user=user, kind=kind, calendar_date__in=dates).exists():
        raise ValueError("calendar_commitment_already_exists")
    periods_by_range = {}
    periods = {}
    for day, start, end in attachments:
        period_range = (start, end)
        if period_range not in periods_by_range:
            periods_by_range[period_range] = calendar_foods_for_period(
                user, start_date=start, end_date=end,
            )
        periods[day] = periods_by_range[period_range]
    attachment_ranges = {day: (start, end) for day, start, end in attachments}
    commitments = [
        CalendarCommitment(
            user=user, kind=kind, calendar_date=day, note=day_notes.get(day, clean_note),
            food_period_start=attachment_ranges[day][0] if day in attachment_ranges else None,
            food_period_end=attachment_ranges[day][1] if day in attachment_ranges else None,
            food_plans_count=periods[day]["plans_count"] if day in periods else 0,
            foods_snapshot=deepcopy(periods[day]["foods_aggregation_table"]) if day in periods else [],
        )
        for day in sorted(dates)
    ]
    try:
        return CalendarCommitment.objects.bulk_create(commitments)
    except IntegrityError as exc:
        raise ValueError("calendar_commitment_already_exists") from exc
