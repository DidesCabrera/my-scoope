from __future__ import annotations

from datetime import date, datetime

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from notas.application.services.calendarization.scheduling import local_date_for_timezone
from notas.application.services.calendarization.snapshots import (
    build_dailyplan_snapshot_from_dailyplan,
    dailyplan_with_calendarization_content,
)
from notas.application.services.commands.dailyplan_commands import create_draft_dailyplan
from notas.application.services.commands.pinned_dailyplan_commands import default_today_plan_name
from notas.domain.models import CalendarizedDay, DailyPlan, PinnedDailyPlan, ScheduledNotificationEvent


def _today_for_user(user, *, now: datetime | None = None) -> date:
    return local_date_for_timezone(user.profile.timezone_name or "UTC", now=now)


def _validate_assignment_key(value: str) -> str:
    key = (value or "").strip()
    if not 8 <= len(key) <= 120:
        raise ValueError("calendar_assignment_key_invalid")
    return key


def _current_day(*, user, local_date: date) -> CalendarizedDay | None:
    return (
        CalendarizedDay.objects.select_for_update()
        .filter(user=user, calendar_date=local_date, assignment_state=CalendarizedDay.STATE_CURRENT)
        .first()
    )


def _ensure_day_replaceable(day: CalendarizedDay, *, today: date) -> None:
    if day.calendar_date < today or day.meal_execution_events.exists():
        raise ValueError("calendar_day_has_execution")


def _supersede_day(day: CalendarizedDay, *, reason: str, now: datetime) -> None:
    _cancel_day_events(day, reason=reason)
    day.assignment_state = CalendarizedDay.STATE_SUPERSEDED
    day.change_reason = reason
    day.state_changed_at = now
    day.save(update_fields=["assignment_state", "change_reason", "state_changed_at"])


def _cancel_day_events(day: CalendarizedDay, *, reason: str) -> None:
    day.notification_events.filter(
        status__in=(ScheduledNotificationEvent.STATUS_PENDING, ScheduledNotificationEvent.STATUS_PROCESSING)
    ).update(status=ScheduledNotificationEvent.STATUS_CANCELLED, skip_reason=reason, claimed_at=None)


@transaction.atomic
def assign_dailyplan_to_calendar_date(
    *,
    user,
    dailyplan_id: int,
    local_date: date,
    assignment_key: str,
    replace_existing: bool = False,
    now: datetime | None = None,
) -> CalendarizedDay:
    """Create one dated snapshot. The source plan is never read as the live day."""
    assignment_key = _validate_assignment_key(assignment_key)
    existing_key = CalendarizedDay.objects.filter(assignment_key=assignment_key).first()
    if existing_key is not None:
        if (
            existing_key.user_id == user.id
            and existing_key.calendar_date == local_date
            and existing_key.source_dailyplan_id == dailyplan_id
        ):
            return existing_key
        raise ValueError("calendar_assignment_key_conflict")

    current_time = now or timezone.now()
    if local_date < _today_for_user(user, now=current_time):
        raise ValueError("calendar_date_in_past")
    User.objects.select_for_update().get(pk=user.pk)
    try:
        source = DailyPlan.objects.exclude(source=DailyPlan.SOURCE_PROGRAM).get(
            pk=dailyplan_id, created_by=user
        )
    except DailyPlan.DoesNotExist as exc:
        raise ValueError("calendar_dailyplan_not_owned") from exc
    current = _current_day(user=user, local_date=local_date)
    if current is not None:
        _ensure_day_replaceable(current, today=_today_for_user(user, now=current_time))
        if not replace_existing:
            raise ValueError("calendar_replacement_confirmation_required")
        _supersede_day(current, reason="manual_plan_replaced", now=current_time)

    dailyplan = dailyplan_with_calendarization_content(source.id)
    snapshot = build_dailyplan_snapshot_from_dailyplan(dailyplan)
    day = CalendarizedDay.objects.create(
        user=user,
        calendar_date=local_date,
        source_kind=CalendarizedDay.SOURCE_MANUAL,
        source_dailyplan_id=source.id,
        assignment_state=CalendarizedDay.STATE_CURRENT,
        assignment_key=assignment_key,
        plan_snapshot=snapshot.payload,
        snapshot_hash=snapshot.content_hash,
    )
    if current is not None:
        current.superseded_by = day
        current.save(update_fields=["superseded_by"])
    if local_date == _today_for_user(user, now=current_time):
        # Keep legacy check-ins, but prevent a live library pin from resurfacing
        # if this dated assignment is later removed.
        PinnedDailyPlan.objects.filter(user=user, is_active=True).update(is_active=False)
    return day


@transaction.atomic
def remove_calendar_date_plan(*, user, local_date: date, now: datetime | None = None) -> CalendarizedDay:
    current_time = now or timezone.now()
    today = _today_for_user(user, now=current_time)
    if local_date < today:
        raise ValueError("calendar_date_in_past")
    User.objects.select_for_update().get(pk=user.pk)
    day = _current_day(user=user, local_date=local_date)
    if day is None:
        raise ValueError("calendar_day_not_found")
    _ensure_day_replaceable(day, today=today)
    _cancel_day_events(day, reason="calendar_plan_removed")
    day.assignment_state = CalendarizedDay.STATE_REMOVED
    day.change_reason = "calendar_plan_removed"
    day.state_changed_at = current_time
    day.save(update_fields=["assignment_state", "change_reason", "state_changed_at"])
    return day


@transaction.atomic
def create_and_assign_draft_to_calendar_date(
    *, user, local_date: date, assignment_key: str, now: datetime | None = None
) -> CalendarizedDay:
    assignment_key = _validate_assignment_key(assignment_key)
    existing = CalendarizedDay.objects.filter(assignment_key=assignment_key).first()
    if existing is not None:
        if existing.user_id == user.id and existing.calendar_date == local_date:
            return existing
        raise ValueError("calendar_assignment_key_conflict")
    created = create_draft_dailyplan(user=user, name=default_today_plan_name(local_date))
    return assign_dailyplan_to_calendar_date(
        user=user,
        dailyplan_id=created.dailyplan.id,
        local_date=local_date,
        assignment_key=assignment_key,
        now=now,
    )


@transaction.atomic
def move_calendar_date_plan(
    *,
    user,
    source_date: date,
    target_date: date,
    assignment_key: str,
    replace_existing: bool = False,
    now: datetime | None = None,
) -> CalendarizedDay:
    """Move a manual snapshot without changing its source library plan or losing either dated version."""
    assignment_key = _validate_assignment_key(assignment_key)
    if source_date == target_date:
        raise ValueError("calendar_move_same_date")
    current_time = now or timezone.now()
    today = _today_for_user(user, now=current_time)
    if source_date < today or target_date < today:
        raise ValueError("calendar_date_in_past")
    User.objects.select_for_update().get(pk=user.pk)
    existing_key = CalendarizedDay.objects.filter(assignment_key=assignment_key).first()
    if existing_key is not None:
        if (
            existing_key.user_id == user.id
            and existing_key.calendar_date == target_date
            and CalendarizedDay.objects.filter(
                user=user, calendar_date=source_date, superseded_by=existing_key,
                change_reason="manual_plan_moved",
            ).exists()
        ):
            return existing_key
        raise ValueError("calendar_assignment_key_conflict")
    source = _current_day(user=user, local_date=source_date)
    if source is None:
        raise ValueError("calendar_day_not_found")
    if source.source_kind != CalendarizedDay.SOURCE_MANUAL:
        raise ValueError("calendar_move_program_day_unsupported")
    _ensure_day_replaceable(source, today=today)
    target = _current_day(user=user, local_date=target_date)
    if target is not None:
        _ensure_day_replaceable(target, today=today)
        if not replace_existing:
            raise ValueError("calendar_replacement_confirmation_required")
    _supersede_day(source, reason="manual_plan_moved", now=current_time)
    if target is not None:
        _supersede_day(target, reason="manual_plan_replaced_by_move", now=current_time)
    moved = CalendarizedDay.objects.create(
        user=user,
        calendar_date=target_date,
        source_kind=CalendarizedDay.SOURCE_MANUAL,
        source_dailyplan_id=source.source_dailyplan_id,
        assignment_state=CalendarizedDay.STATE_CURRENT,
        assignment_key=assignment_key,
        plan_snapshot=source.plan_snapshot,
        snapshot_hash=source.snapshot_hash,
    )
    source.superseded_by = moved
    source.save(update_fields=["superseded_by"])
    if target is not None:
        target.superseded_by = moved
        target.save(update_fields=["superseded_by"])
    return moved
