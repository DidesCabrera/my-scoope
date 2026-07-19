from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone


DAILY_NOTIFICATION_GRACE = timedelta(hours=2)
MEAL_NOTIFICATION_GRACE = timedelta(minutes=15)


@dataclass(frozen=True)
class ScheduledWindow:
    scheduled_for_utc: datetime
    available_until_utc: datetime
    dst_resolution: str = "exact"


def validate_timezone_name(value: str) -> str:
    clean_value = (value or "").strip()
    if not clean_value or len(clean_value) > 64:
        raise ValueError("calendarization_timezone_invalid")
    try:
        ZoneInfo(clean_value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("calendarization_timezone_invalid")
    return clean_value


def local_date_for_timezone(timezone_name: str, *, now: datetime | None = None) -> date:
    zone = ZoneInfo(validate_timezone_name(timezone_name))
    current = now or timezone.now()
    if timezone.is_naive(current):
        current = current.replace(tzinfo=dt_timezone.utc)
    return current.astimezone(zone).date()


def _roundtrips(naive_value: datetime, zone: ZoneInfo, fold: int) -> tuple[bool, datetime]:
    localized = naive_value.replace(tzinfo=zone, fold=fold)
    utc_value = localized.astimezone(dt_timezone.utc)
    roundtrip = utc_value.astimezone(zone).replace(tzinfo=None)
    return roundtrip == naive_value, utc_value


def local_datetime_to_utc(local_date: date, local_time: time, timezone_name: str) -> tuple[datetime, str]:
    zone = ZoneInfo(validate_timezone_name(timezone_name))
    naive_value = datetime.combine(local_date, local_time.replace(tzinfo=None))

    valid_fold_zero, fold_zero_utc = _roundtrips(naive_value, zone, 0)
    if valid_fold_zero:
        return fold_zero_utc, "first_occurrence" if _roundtrips(naive_value, zone, 1)[1] != fold_zero_utc else "exact"

    for offset_minutes in range(1, 181):
        candidate = naive_value + timedelta(minutes=offset_minutes)
        valid, candidate_utc = _roundtrips(candidate, zone, 0)
        if valid:
            return candidate_utc, "first_valid_after_gap"

    raise ValueError("calendarization_local_time_unresolvable")


def build_scheduled_window(
    *,
    local_date: date,
    local_time: time,
    timezone_name: str,
    grace: timedelta = DAILY_NOTIFICATION_GRACE,
) -> ScheduledWindow:
    scheduled_for_utc, resolution = local_datetime_to_utc(local_date, local_time, timezone_name)
    return ScheduledWindow(
        scheduled_for_utc=scheduled_for_utc,
        available_until_utc=scheduled_for_utc + grace,
        dst_resolution=resolution,
    )

