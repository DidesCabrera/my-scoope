from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import ceil
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.urls import reverse
from django.utils import timezone

from notas.application.queries.calendarization_execution_queries import (
    calendarization_progress_summary,
    meal_execution_state_for_day,
)
from notas.application.queries.calendarization_projection_queries import (
    build_calendarization_snapshot_projection,
    snapshot_nutrition_totals,
)
from notas.application.queries.calendarization_queries import (
    current_calendarization_for_user,
    today_for_calendarization,
)
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.services.nutrition import macro_kcal_distribution
from notas.presentation.resolvers.title_resolvers import resolve_category_badge
from notas.presentation.viewmodels.content.dailyplan.list_vm import (
    KPIUI,
    ChildCardUI,
    FoodsAggregationUI,
    MenuUI,
    MetadataUI,
    StructuralIndicatorsUI,
    TitleUI,
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
    calendarized_meals: list[dict]
    completed_meals_count: int
    noted_meals_count: int


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
    start_date: str
    end_date: str
    duration_label: str
    duration_days_label: str
    progress_day: int
    progress_total_days: int
    progress_percent: int
    elapsed_days: int
    total_days: int
    progress: int
    adhered_days: int
    planned_adherence_days: int
    adherence: int
    weeks_count: int
    assigned_plans_count: int
    foods_count: int
    active_week_summary: dict | None
    dashboard_url: str
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
    today = today_for_calendarization(calendarization, now=now) if calendarization else _today_for_user(user, now=now)
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
    calendarized_days = {day.calendar_date: day for day in (calendarization.days.all() if calendarization else ())}
    projection = (
        build_calendarization_snapshot_projection(calendarization)
        if calendarization
        else None
    )
    current_weight = get_current_weight(user) if calendarization else None
    owner_label = str(user)

    weeks = [
        _build_week_vm(
            week_monday=week_monday,
            active_monday=monday,
            selected_date=selected_date,
            today=today,
            calendarized_days=calendarized_days,
            current_weight=current_weight,
            owner_label=owner_label,
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
    adherence_summary = None
    if calendarization and today >= calendarization.start_date:
        adherence_summary = calendarization_progress_summary(
            calendarization,
            period_start=calendarization.start_date,
            period_end=min(today, calendarization.end_date),
        )
    active_week_number = ((monday - week_starts[0]).days // 7) + 1 if calendarization else 1
    active_week_summary = next(
        (
            week
            for week in (projection["weeks"] if projection else [])
            if week["week_number"] == active_week_number
        ),
        None,
    )

    return HomeCalendarizationVM(
        has_calendarization=calendarization is not None,
        program_name=calendarization.program_name_snapshot if calendarization else "",
        status_label=STATUS_LABELS.get(calendarization.status, calendarization.status.title())
        if calendarization
        else "",
        start_label=_compact_date_label(calendarization.start_date) if calendarization else "",
        end_label=_compact_date_label(calendarization.end_date) if calendarization else "",
        start_date=_compact_date_label(calendarization.start_date) if calendarization else "",
        end_date=_compact_date_label(calendarization.end_date) if calendarization else "",
        duration_label=_duration_label(calendarization.start_date, calendarization.end_date) if calendarization else "",
        duration_days_label=_duration_days_label(progress_total_days) if calendarization else "",
        progress_day=progress_day,
        progress_total_days=progress_total_days,
        progress_percent=progress_percent,
        elapsed_days=progress_day,
        total_days=progress_total_days,
        progress=progress_percent,
        adhered_days=adherence_summary["completed_meals"] if adherence_summary else 0,
        planned_adherence_days=adherence_summary["elapsed_meals"] if adherence_summary else 0,
        adherence=adherence_summary["adherence_percent"] if adherence_summary else 0,
        weeks_count=projection["duration_weeks"] if projection else 0,
        assigned_plans_count=projection["filled_days_count"] if projection else 0,
        foods_count=projection["program_foods_count"] if projection else 0,
        active_week_summary=active_week_summary,
        dashboard_url=reverse("calendarization_dashboard"),
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
    current_weight,
    owner_label: str,
    navigation_view_name: str,
) -> HomeCalendarWeekVM:
    is_active_week = week_monday == active_monday
    days = []
    for offset in range(7):
        calendar_date = week_monday + timedelta(days=offset)
        calendarized_day = calendarized_days.get(calendar_date)
        has_plan = bool(calendarized_day and calendarized_day.has_plan)
        dailyplan_card = (
            _build_snapshot_dailyplan_card(
                calendarized_day,
                current_weight=current_weight,
                owner_label=owner_label,
            )
            if is_active_week and has_plan
            else None
        )
        execution = meal_execution_state_for_day(calendarized_day) if has_plan else []
        state_by_key = {item["meal_key"]: item for item in execution}
        calendarized_meals = []
        for meal in (calendarized_day.plan_snapshot or {}).get("meals", []) if calendarized_day else []:
            if not isinstance(meal, dict):
                continue
            meal_key = meal.get("key") or ""
            meal_state = state_by_key.get(meal_key, {"status": "planned", "note": ""})
            calendarized_meals.append(
                {
                    "key": meal_key,
                    "name": meal.get("name") or "Comida",
                    "hour": meal.get("hour"),
                    "foods": [
                        food.get("name") or "Alimento" for food in meal.get("foods", []) if isinstance(food, dict)
                    ],
                    "detail_url": reverse(
                        "calendarization_meal_detail",
                        args=[calendarized_day.id, meal_key],
                    )
                    if meal_key
                    else None,
                    "completed": meal_state["status"] == "completed",
                    "has_note": bool(meal_state["note"].strip()),
                }
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
                detail_url=(reverse("calendarization_day_detail", args=[calendarized_day.id]) if has_plan else None),
                plan_snapshot=(calendarized_day.plan_snapshot if has_plan else None),
                dailyplan_card=dailyplan_card,
                calendarized_meals=calendarized_meals,
                completed_meals_count=sum(item["completed"] for item in calendarized_meals),
                noted_meals_count=sum(item["has_note"] for item in calendarized_meals),
            )
        )
    return HomeCalendarWeekVM(
        week_start_iso=week_monday.isoformat(),
        is_active=is_active_week,
        days=days,
    )


def _percentage(part: float, total: float) -> float:
    return (part / total) * 100 if total > 0 else 0


def _snapshot_meal_table_items(snapshot: dict, plan_totals: dict) -> list[dict]:
    items = []
    for index, meal in enumerate(snapshot.get("meals", [])):
        if not isinstance(meal, dict):
            continue
        totals = snapshot_nutrition_totals({"totals": meal.get("totals") or {}})
        items.append(
            {
                "main_id": snapshot.get("source", {}).get("dailyplan_id"),
                "child_id": meal.get("key") or index,
                "rel": {
                    "id": meal.get("key") or index,
                    "hour": meal.get("hour"),
                    "note": meal.get("note") or "",
                    "name": meal.get("name") or "Comida",
                    "total_kcal": totals["total_kcal"],
                    "kcal_share": _percentage(
                        totals["total_kcal"],
                        plan_totals["total_kcal"],
                    ),
                    "kcal_distribution": macro_kcal_distribution(
                        totals["kcal_protein"],
                        totals["kcal_carbs"],
                        totals["kcal_fat"],
                    ),
                    "g_protein": totals["protein"],
                    "g_carbs": totals["carbs"],
                    "g_fat": totals["fat"],
                    "alloc_protein": _percentage(
                        totals["kcal_protein"],
                        plan_totals["kcal_protein"],
                    ),
                    "alloc_carbs": _percentage(
                        totals["kcal_carbs"],
                        plan_totals["kcal_carbs"],
                    ),
                    "alloc_fat": _percentage(
                        totals["kcal_fat"],
                        plan_totals["kcal_fat"],
                    ),
                },
            }
        )
    return items


def _build_snapshot_dailyplan_card(day, *, current_weight, owner_label: str) -> ChildCardUI:
    snapshot = day.plan_snapshot
    totals = snapshot_nutrition_totals(snapshot)
    meals = [meal for meal in snapshot.get("meals", []) if isinstance(meal, dict)]
    food_names = {
        str(food.get("name") or "Alimento").strip().casefold()
        for meal in meals
        for food in meal.get("foods", [])
        if isinstance(food, dict)
    }
    detail_url = reverse("calendarization_day_detail", args=[day.id])
    return ChildCardUI(
        child_id=day.id,
        titulo=TitleUI(
            name=snapshot.get("name") or "Plan diario",
            label="DailyPlan",
            icon="clipboard-list",
            category="en plan",
            category_badge=resolve_category_badge("en plan"),
            structural_indicators=StructuralIndicatorsUI(
                meals_count=len(meals),
                foods_count=len(food_names),
            ),
            url=detail_url,
        ),
        kpis=KPIUI(
            ppk=(totals["protein"] / current_weight) if current_weight else 0,
            tot_kcal=totals["total_kcal"],
            g_protein=totals["protein"],
            g_carbs=totals["carbs"],
            g_fat=totals["fat"],
            kcal_protein=totals["kcal_protein"],
            kcal_carbs=totals["kcal_carbs"],
            kcal_fat=totals["kcal_fat"],
            alloc_protein=totals["alloc"]["protein"],
            alloc_carbs=totals["alloc"]["carbs"],
            alloc_fat=totals["alloc"]["fat"],
        ),
        table={"items": _snapshot_meal_table_items(snapshot, totals)},
        menu=MenuUI(meals=[]),
        foods_aggregation=FoodsAggregationUI(foods_aggregation=[]),
        metadata=MetadataUI(
            owner=owner_label,
            author=owner_label,
            fork_from=None,
        ),
        actions=[
            {
                "key": "detail",
                "label": "Ver detalle",
                "url": detail_url,
                "method": "get",
                "icon": "chevron-right",
                "desktop_position": "inline",
                "mobile_position": "inline",
                "extra_class": "",
            }
        ],
    )
