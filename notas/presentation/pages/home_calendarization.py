from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import ceil
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.urls import reverse
from django.utils import timezone

from notas.application.queries.calendarization_queries import (
    current_calendarization_for_user,
    today_for_calendarization,
)
from notas.domain.models import DailyPlan
from notas.presentation.config.viewmodel_config import DAILYPLAN_VIEWMODE_PERSONAL_LIST
from notas.presentation.viewmodels.dailyplans import (
    build_dailyplan_list_content_data,
    build_dailyplan_list_vm,
)

WEEKDAY_LABELS = ("L", "M", "M", "J", "V", "S", "D")
WEEKDAY_NAMES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MONTH_LABELS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
MONTH_NAMES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
STATUS_LABELS = {
    "scheduled": "Programado",
    "active": "Activo",
    "paused": "Pausado",
}


@dataclass(frozen=True)
class HomeCalendarDayVM:
    panel_id: str
    weekday_label: str
    date_number: int
    month_label: str
    iso_date: str
    accessible_date: str
    temporal_state: str
    is_today: bool
    is_selected: bool
    is_active_week: bool
    has_plan: bool
    plan_name: str
    selection_url: str
    detail_url: str | None
    plan_snapshot: dict | None
    dailyplan_card: object | None


@dataclass(frozen=True)
class HomeCalendarWeekVM:
    week_start_iso: str
    is_active: bool
    days: list[HomeCalendarDayVM]


@dataclass(frozen=True)
class HomeCalendarizationVM:
    has_calendarization: bool
    program_name: str
    status_label: str
    start_label: str
    end_label: str
    duration_label: str
    duration_days_label: str
    progress_day: int
    progress_total_days: int
    progress_percent: int
    dashboard_url: str
    previous_week_url: str
    next_week_url: str
    has_multiple_weeks: bool
    days: list[HomeCalendarDayVM]
    weeks: list[HomeCalendarWeekVM]


def _today_for_user(user, *, now: datetime | None = None) -> date:
    instant = now or timezone.now()
    timezone_name = getattr(user.profile, "timezone_name", "") or "UTC"
    try:
        user_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        user_timezone = ZoneInfo("UTC")
    return instant.astimezone(user_timezone).date()


def _accessible_date(value: date, *, is_today: bool) -> str:
    label = f"{WEEKDAY_NAMES[value.weekday()]} {value.day} de {MONTH_NAMES[value.month - 1]}"
    return f"{label}, hoy" if is_today else label


def _compact_date_label(value: date) -> str:
    return f"{value.day}{MONTH_LABELS[value.month - 1]}"


def _week_start_from_param(value: str | None, fallback: date) -> date:
    if value:
        try:
            selected_date = date.fromisoformat(value)
        except ValueError:
            selected_date = fallback
    else:
        selected_date = fallback
    return selected_date - timedelta(days=selected_date.weekday())


def _calendar_week_url(view_name: str, monday: date) -> str:
    return f"{reverse(view_name)}?{urlencode({'calendar_week': monday.isoformat()})}"


def _calendar_day_url(view_name: str, monday: date, selected_date: date) -> str:
    query = urlencode(
        {
            "calendar_week": monday.isoformat(),
            "calendar_date": selected_date.isoformat(),
        }
    )
    return f"{reverse(view_name)}?{query}"


def _duration_label(start_date: date, end_date: date) -> str:
    weeks = max(1, ceil(((end_date - start_date).days + 1) / 7))
    unit = "semana" if weeks == 1 else "semanas"
    return f"{weeks} {unit}"


def _duration_days_label(total_days: int) -> str:
    unit = "día" if total_days == 1 else "días"
    return f"{total_days} {unit}"


def _calendarization_progress(calendarization, today: date) -> tuple[int, int, int]:
    if not calendarization:
        return 0, 0, 0

    total_days = max(1, (calendarization.end_date - calendarization.start_date).days + 1)
    elapsed_days = (today - calendarization.start_date).days + 1
    progress_day = min(max(elapsed_days, 0), total_days)
    progress_percent = round((progress_day / total_days) * 100)
    return progress_day, total_days, progress_percent


def _calendarization_week_starts(calendarization, fallback_monday: date) -> list[date]:
    if not calendarization:
        return [fallback_monday]

    first_monday = calendarization.start_date - timedelta(days=calendarization.start_date.weekday())
    last_monday = calendarization.end_date - timedelta(days=calendarization.end_date.weekday())
    week_count = ((last_monday - first_monday).days // 7) + 1
    return [first_monday + timedelta(days=week * 7) for week in range(week_count)]


def _bounded_active_monday(requested_monday: date, week_starts: list[date], today_monday: date) -> date:
    if requested_monday in week_starts:
        return requested_monday
    if today_monday in week_starts:
        return today_monday
    return week_starts[0]


def build_home_calendarization_vm(
    user,
    *,
    now: datetime | None = None,
    request_get=None,
    navigation_view_name: str = "home_view",
) -> HomeCalendarizationVM:
    calendarization = current_calendarization_for_user(user)
    today = (
        today_for_calendarization(calendarization, now=now)
        if calendarization
        else _today_for_user(user, now=now)
    )
    today_monday = today - timedelta(days=today.weekday())
    requested_monday = _week_start_from_param(
        (request_get or {}).get("calendar_week"),
        today_monday,
    )
    week_starts = _calendarization_week_starts(calendarization, today_monday)
    monday = _bounded_active_monday(requested_monday, week_starts, today_monday)
    requested_selected_date = _date_from_param((request_get or {}).get("calendar_date"))
    selected_date = (
        requested_selected_date
        if requested_selected_date and _week_start_from_param(requested_selected_date.isoformat(), monday) == monday
        else (today if monday == today_monday else monday)
    )
    calendarized_days = {
        day.calendar_date: day
        for day in (calendarization.days.all() if calendarization else ())
    }
    dailyplans_by_id = _dailyplan_cards_by_id(user, calendarized_days.values())

    weeks = [
        _build_week_vm(
            week_monday=week_monday,
            active_monday=monday,
            selected_date=selected_date,
            today=today,
            calendarized_days=calendarized_days,
            dailyplans_by_id=dailyplans_by_id,
            navigation_view_name=navigation_view_name,
        )
        for week_monday in week_starts
    ]
    active_week = next((week for week in weeks if week.is_active), weeks[0])
    days = active_week.days
    progress_day, progress_total_days, progress_percent = _calendarization_progress(
        calendarization,
        today,
    )

    return HomeCalendarizationVM(
        has_calendarization=calendarization is not None,
        program_name=calendarization.program_name_snapshot if calendarization else "",
        status_label=STATUS_LABELS.get(calendarization.status, calendarization.status.title()) if calendarization else "",
        start_label=_compact_date_label(calendarization.start_date) if calendarization else "",
        end_label=_compact_date_label(calendarization.end_date) if calendarization else "",
        duration_label=_duration_label(calendarization.start_date, calendarization.end_date) if calendarization else "",
        duration_days_label=_duration_days_label(progress_total_days) if calendarization else "",
        progress_day=progress_day,
        progress_total_days=progress_total_days,
        progress_percent=progress_percent,
        dashboard_url=reverse("calendarization_dashboard"),
        previous_week_url=_calendar_week_url(navigation_view_name, monday - timedelta(days=7)),
        next_week_url=_calendar_week_url(navigation_view_name, monday + timedelta(days=7)),
        has_multiple_weeks=len(weeks) > 1,
        days=days,
        weeks=weeks,
    )


def _date_from_param(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _build_week_vm(
    *,
    week_monday: date,
    active_monday: date,
    selected_date: date,
    today: date,
    calendarized_days,
    dailyplans_by_id,
    navigation_view_name: str,
) -> HomeCalendarWeekVM:
    is_active_week = week_monday == active_monday
    days = []
    for offset in range(7):
        calendar_date = week_monday + timedelta(days=offset)
        calendarized_day = calendarized_days.get(calendar_date)
        has_plan = bool(calendarized_day and calendarized_day.has_plan)
        dailyplan_card = (
            dailyplans_by_id.get(calendarized_day.source_dailyplan_id)
            if is_active_week and has_plan and calendarized_day.source_dailyplan_id
            else None
        )
        is_today = calendar_date == today
        temporal_state = "today" if is_today else ("past" if calendar_date < today else "future")
        days.append(
            HomeCalendarDayVM(
                panel_id=f"home-calendar-plan-{calendar_date.isoformat()}",
                weekday_label=WEEKDAY_LABELS[offset],
                date_number=calendar_date.day,
                month_label=MONTH_LABELS[calendar_date.month - 1],
                iso_date=calendar_date.isoformat(),
                accessible_date=_accessible_date(calendar_date, is_today=is_today),
                temporal_state=temporal_state,
                is_today=is_today,
                is_selected=is_active_week and calendar_date == selected_date,
                is_active_week=is_active_week,
                has_plan=has_plan,
                plan_name=(calendarized_day.plan_snapshot.get("name", "") if has_plan else ""),
                selection_url=_calendar_day_url(navigation_view_name, week_monday, calendar_date),
                detail_url=(
                    reverse("calendarization_day_detail", args=[calendarized_day.id])
                    if has_plan
                    else None
                ),
                plan_snapshot=(calendarized_day.plan_snapshot if has_plan else None),
                dailyplan_card=dailyplan_card,
            )
        )
    return HomeCalendarWeekVM(
        week_start_iso=week_monday.isoformat(),
        is_active=is_active_week,
        days=days,
    )


def _dailyplan_cards_by_id(user, calendarized_days) -> dict[int, object]:
    dailyplan_ids = [
        day.source_dailyplan_id
        for day in calendarized_days
        if day.source_dailyplan_id and day.has_plan
    ]

    if not dailyplan_ids:
        return {}

    dailyplans = (
        DailyPlan.objects.filter(id__in=dailyplan_ids)
        .select_related("created_by", "original_author", "forked_from")
        .prefetch_related("shares", "dailyplan_meals__meal__meal_food_set__food")
        .order_by("id")
    )
    content_data = build_dailyplan_list_content_data(
        dailyplans=dailyplans,
        user=user,
        viewmode=DAILYPLAN_VIEWMODE_PERSONAL_LIST,
    )
    list_vm = build_dailyplan_list_vm(content_data)
    return {card.child_id: card for card in list_vm.child_cards}
