from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
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
    has_plan: bool
    plan_name: str
    detail_url: str | None
    plan_snapshot: dict | None
    dailyplan_card: object | None


@dataclass(frozen=True)
class HomeCalendarizationVM:
    has_calendarization: bool
    program_name: str
    dashboard_url: str
    days: list[HomeCalendarDayVM]


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


def build_home_calendarization_vm(user, *, now: datetime | None = None) -> HomeCalendarizationVM:
    calendarization = current_calendarization_for_user(user)
    today = (
        today_for_calendarization(calendarization, now=now)
        if calendarization
        else _today_for_user(user, now=now)
    )
    monday = today - timedelta(days=today.weekday())
    calendarized_days = {
        day.calendar_date: day
        for day in (calendarization.days.all() if calendarization else ())
    }
    dailyplans_by_id = _dailyplan_cards_by_id(user, calendarized_days.values())

    days = []
    for offset in range(7):
        calendar_date = monday + timedelta(days=offset)
        calendarized_day = calendarized_days.get(calendar_date)
        has_plan = bool(calendarized_day and calendarized_day.has_plan)
        dailyplan_card = (
            dailyplans_by_id.get(calendarized_day.source_dailyplan_id)
            if has_plan and calendarized_day.source_dailyplan_id
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
                has_plan=has_plan,
                plan_name=(calendarized_day.plan_snapshot.get("name", "") if has_plan else ""),
                detail_url=(
                    reverse("calendarization_day_detail", args=[calendarized_day.id])
                    if has_plan
                    else None
                ),
                plan_snapshot=(calendarized_day.plan_snapshot if has_plan else None),
                dailyplan_card=dailyplan_card,
            )
        )

    return HomeCalendarizationVM(
        has_calendarization=calendarization is not None,
        program_name=calendarization.program_name_snapshot if calendarization else "",
        dashboard_url=reverse("calendarization_dashboard"),
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
