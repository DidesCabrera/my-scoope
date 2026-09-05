from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from notas.application.queries.calendarization_execution_queries import (
    calendarization_measurement_summary,
    calendarization_progress_summary,
)
from notas.application.queries.calendarization_queries import current_calendarization_for_user
from notas.application.services.calendarization.scheduling import local_date_for_timezone
from notas.application.services.calendarization.snapshots import SNAPSHOT_SCHEMA_VERSION
from notas.application.services.commands.calendarization_commands import reschedule_calendarized_days
from notas.application.services.nutrition.body_metrics import record_weight
from notas.domain.models import (
    CalendarizationMeasurementContext,
    CalendarizationReview,
    CalendarizationRevision,
    CalendarizedDay,
    CalendarizedMealExecution,
    ProgramCalendarization,
    WeightLog,
)

REVISION_SCHEMA_VERSION = "calendarization_revision.v1"


def _clean_idempotency_key(value: str) -> str:
    clean = (value or "").strip()
    if not 8 <= len(clean) <= 120:
        raise ValueError("calendarization_idempotency_key_invalid")
    return clean


def _owned_day(*, user, day_id: int, for_update: bool = False) -> CalendarizedDay:
    queryset = CalendarizedDay.objects.select_related("calendarization")
    if for_update:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(pk=day_id, calendarization__user=user)
    except CalendarizedDay.DoesNotExist as exc:
        raise ValueError("calendarized_day_not_found") from exc


def _meal_keys(day: CalendarizedDay) -> set[str]:
    return {
        meal.get("key")
        for meal in (day.plan_snapshot or {}).get("meals", [])
        if isinstance(meal, dict) and meal.get("key")
    }


@transaction.atomic
def record_meal_execution(
    *,
    user,
    day_id: int,
    meal_snapshot_key: str,
    action: str,
    idempotency_key: str,
    note: str = "",
    occurred_at: datetime | None = None,
) -> CalendarizedMealExecution:
    idempotency_key = _clean_idempotency_key(idempotency_key)
    existing = CalendarizedMealExecution.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if (
            existing.calendarized_day_id == day_id
            and existing.meal_snapshot_key == meal_snapshot_key
            and existing.action == action
            and existing.calendarized_day.calendarization.user_id == user.id
        ):
            return existing
        raise ValueError("calendarization_idempotency_conflict")

    day = _owned_day(user=user, day_id=day_id, for_update=True)
    calendarization = day.calendarization
    local_today = local_date_for_timezone(calendarization.timezone_name)
    if (
        calendarization.status == ProgramCalendarization.STATUS_SCHEDULED
        and calendarization.start_date <= local_today <= calendarization.end_date
    ):
        calendarization.status = ProgramCalendarization.STATUS_ACTIVE
        calendarization.save(update_fields=["status", "updated_at"])
    if calendarization.status != ProgramCalendarization.STATUS_ACTIVE or day.calendar_date != local_today:
        raise ValueError("meal_execution_not_today")
    if meal_snapshot_key not in _meal_keys(day):
        raise ValueError("meal_snapshot_key_invalid")
    if action not in dict(CalendarizedMealExecution.ACTION_CHOICES):
        raise ValueError("meal_execution_action_invalid")
    clean_note = (note or "").strip()
    if len(clean_note) > 500:
        raise ValueError("meal_execution_note_too_long")

    return CalendarizedMealExecution.objects.create(
        calendarized_day=day,
        meal_snapshot_key=meal_snapshot_key,
        action=action,
        idempotency_key=idempotency_key,
        note=clean_note,
        occurred_at=occurred_at,
    )


@transaction.atomic
def record_calendarized_weight(
    *,
    user,
    weight_kg: float,
    measured_on: date | None = None,
) -> tuple[WeightLog, CalendarizationMeasurementContext | None]:
    weight_log = record_weight(
        user,
        weight_kg,
        measured_on=measured_on,
        source=WeightLog.SOURCE_MANUAL,
    )
    calendarization = current_calendarization_for_user(user)
    if calendarization is None or not (calendarization.start_date <= weight_log.date <= calendarization.end_date):
        return weight_log, None
    day = calendarization.days.filter(calendar_date=weight_log.date).first()
    context, _ = CalendarizationMeasurementContext.objects.get_or_create(
        calendarization=calendarization,
        weight_log=weight_log,
        defaults={"calendarized_day": day},
    )
    return weight_log, context


def _validate_score(value: int | None) -> int | None:
    if value is not None and value not in range(1, 6):
        raise ValueError("calendarization_review_score_invalid")
    return value


@transaction.atomic
def create_calendarization_review(
    *,
    user,
    period_start: date,
    period_end: date,
    idempotency_key: str,
    energy_score: int | None = None,
    hunger_score: int | None = None,
    training_performance_score: int | None = None,
    note: str = "",
) -> CalendarizationReview:
    idempotency_key = _clean_idempotency_key(idempotency_key)
    existing = CalendarizationReview.objects.filter(idempotency_key=idempotency_key).select_related("calendarization").first()
    if existing:
        if existing.calendarization.user_id == user.id:
            return existing
        raise ValueError("calendarization_idempotency_conflict")

    calendarization = current_calendarization_for_user(user)
    if calendarization is None:
        raise ValueError("calendarization_not_found")
    local_today = local_date_for_timezone(calendarization.timezone_name)
    if (
        period_start > period_end
        or period_start < calendarization.start_date
        or period_end > min(local_today, calendarization.end_date)
    ):
        raise ValueError("calendarization_review_period_invalid")
    clean_note = (note or "").strip()
    if len(clean_note) > 1000:
        raise ValueError("calendarization_review_note_too_long")

    adherence = calendarization_progress_summary(
        calendarization,
        period_start=period_start,
        period_end=period_end,
    )
    measurements = calendarization_measurement_summary(
        calendarization,
        period_start=period_start,
        period_end=period_end,
    )
    return CalendarizationReview.objects.create(
        calendarization=calendarization,
        period_start=period_start,
        period_end=period_end,
        energy_score=_validate_score(energy_score),
        hunger_score=_validate_score(hunger_score),
        training_performance_score=_validate_score(training_performance_score),
        note=clean_note,
        summary_snapshot={
            "schema_version": "calendarization_review.v1",
            "adherence": adherence,
            "measurements": measurements,
        },
        idempotency_key=idempotency_key,
    )


def _canonical_hash(payload: dict) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validated_snapshot(payload: dict) -> dict:
    if not isinstance(payload, dict) or payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError("calendarization_revision_snapshot_invalid")
    meals = payload.get("meals")
    if not isinstance(meals, list):
        raise ValueError("calendarization_revision_snapshot_invalid")
    keys = [meal.get("key") for meal in meals if isinstance(meal, dict)]
    if len(keys) != len(meals) or any(not key or len(key) > 80 for key in keys) or len(keys) != len(set(keys)):
        raise ValueError("calendarization_revision_snapshot_invalid")
    return payload


@transaction.atomic
def prepare_calendarization_revision(
    *,
    user,
    calendarization_id: int,
    effective_from: date,
    replacement_days: list[dict],
    rationale: str,
    idempotency_key: str,
    review_id: int | None = None,
    now: datetime | None = None,
) -> CalendarizationRevision:
    idempotency_key = _clean_idempotency_key(idempotency_key)
    existing = CalendarizationRevision.objects.filter(idempotency_key=idempotency_key).select_related("calendarization").first()
    if existing:
        if existing.calendarization.user_id == user.id:
            return existing
        raise ValueError("calendarization_idempotency_conflict")

    try:
        calendarization = ProgramCalendarization.objects.select_for_update().get(pk=calendarization_id, user=user)
    except ProgramCalendarization.DoesNotExist as exc:
        raise ValueError("calendarization_not_found") from exc
    if calendarization.status not in ProgramCalendarization.CURRENT_STATUSES:
        raise ValueError("calendarization_not_current")
    local_today = local_date_for_timezone(calendarization.timezone_name, now=now)
    if effective_from <= local_today or effective_from > calendarization.end_date:
        raise ValueError("calendarization_revision_effective_date_invalid")
    clean_rationale = (rationale or "").strip()
    if not clean_rationale or len(clean_rationale) > 1000:
        raise ValueError("calendarization_revision_rationale_invalid")
    if not replacement_days:
        raise ValueError("calendarization_revision_days_required")

    replacement_by_date: dict[date, dict] = {}
    for item in replacement_days:
        raw_date = item.get("calendar_date")
        target_date = date.fromisoformat(raw_date) if isinstance(raw_date, str) else raw_date
        if not isinstance(target_date, date) or target_date < effective_from or target_date > calendarization.end_date:
            raise ValueError("calendarization_revision_day_invalid")
        if target_date in replacement_by_date:
            raise ValueError("calendarization_revision_day_duplicate")
        replacement_by_date[target_date] = _validated_snapshot(item.get("plan_snapshot"))

    days = list(
        CalendarizedDay.objects.select_for_update()
        .filter(calendarization=calendarization, calendar_date__in=replacement_by_date)
        .order_by("calendar_date")
    )
    if len(days) != len(replacement_by_date):
        raise ValueError("calendarization_revision_day_not_found")
    if CalendarizedMealExecution.objects.filter(calendarized_day__in=days).exists():
        raise ValueError("calendarization_revision_day_already_executed")

    review = None
    if review_id is not None:
        review = CalendarizationReview.objects.filter(pk=review_id, calendarization=calendarization).first()
        if review is None:
            raise ValueError("calendarization_review_not_found")

    before_days = [
        {
            "calendar_date": day.calendar_date.isoformat(),
            "snapshot_hash": day.snapshot_hash,
            "plan_snapshot": day.plan_snapshot,
        }
        for day in days
    ]
    after_days = [
        {
            "calendar_date": day.calendar_date.isoformat(),
            "snapshot_hash": _canonical_hash(replacement_by_date[day.calendar_date]),
            "plan_snapshot": replacement_by_date[day.calendar_date],
        }
        for day in days
    ]
    return CalendarizationRevision.objects.create(
        calendarization=calendarization,
        review=review,
        effective_from=effective_from,
        before_snapshot={"schema_version": REVISION_SCHEMA_VERSION, "days": before_days},
        after_snapshot={"schema_version": REVISION_SCHEMA_VERSION, "days": after_days},
        rationale=clean_rationale,
        idempotency_key=idempotency_key,
    )


@transaction.atomic
def decide_calendarization_revision(
    *,
    user,
    revision_id: int,
    decision: str,
    now: datetime | None = None,
) -> CalendarizationRevision:
    current_time = now or timezone.now()
    try:
        revision = (
            CalendarizationRevision.objects.select_for_update()
            .select_related("calendarization")
            .get(pk=revision_id, calendarization__user=user)
        )
    except CalendarizationRevision.DoesNotExist as exc:
        raise ValueError("calendarization_revision_not_found") from exc
    if revision.status != CalendarizationRevision.STATUS_PENDING:
        raise ValueError("calendarization_revision_already_decided")
    if decision == "reject":
        revision.status = CalendarizationRevision.STATUS_REJECTED
        revision.decided_at = current_time
        revision.save(update_fields=["status", "decided_at", "updated_at"])
        return revision
    if decision != "approve":
        raise ValueError("calendarization_revision_decision_invalid")

    calendarization = revision.calendarization
    if calendarization.status not in ProgramCalendarization.CURRENT_STATUSES:
        raise ValueError("calendarization_revision_no_longer_eligible")
    local_today = local_date_for_timezone(calendarization.timezone_name, now=current_time)
    if revision.effective_from <= local_today:
        raise ValueError("calendarization_revision_no_longer_eligible")

    after_days = revision.after_snapshot.get("days", [])
    replacement_by_date = {
        date.fromisoformat(item["calendar_date"]): _validated_snapshot(item["plan_snapshot"])
        for item in after_days
    }
    days = list(
        CalendarizedDay.objects.select_for_update()
        .filter(calendarization=calendarization, calendar_date__in=replacement_by_date)
        .order_by("calendar_date")
    )
    if len(days) != len(replacement_by_date) or CalendarizedMealExecution.objects.filter(calendarized_day__in=days).exists():
        raise ValueError("calendarization_revision_no_longer_eligible")
    before_by_date = {
        date.fromisoformat(item["calendar_date"]): item
        for item in revision.before_snapshot.get("days", [])
    }
    if set(before_by_date) != set(replacement_by_date) or any(
        day.snapshot_hash != before_by_date[day.calendar_date].get("snapshot_hash")
        or day.plan_snapshot != before_by_date[day.calendar_date].get("plan_snapshot")
        for day in days
    ):
        raise ValueError("calendarization_revision_no_longer_eligible")

    for day in days:
        day.plan_snapshot = replacement_by_date[day.calendar_date]
        day.snapshot_hash = _canonical_hash(day.plan_snapshot)
        day.save(update_fields=["plan_snapshot", "snapshot_hash"])
    reschedule_calendarized_days(
        calendarization=calendarization,
        days=days,
        now=current_time,
        reason="calendarization_revision_applied",
    )
    revision.status = CalendarizationRevision.STATUS_APPLIED
    revision.decided_at = current_time
    revision.applied_at = current_time
    revision.save(update_fields=["status", "decided_at", "applied_at", "updated_at"])
    return revision


def default_review_period(calendarization, *, now: datetime | None = None) -> tuple[date, date]:
    local_today = min(local_date_for_timezone(calendarization.timezone_name, now=now), calendarization.end_date)
    return max(calendarization.start_date, local_today - timedelta(days=6)), local_today
