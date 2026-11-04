from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse

from notas.application.queries.calendar_metrics import calendar_adherence_summary, calendar_future_schedule_summary
from notas.application.services.calendarization.scheduling import local_date_for_timezone
from notas.domain.models import (
    CalendarCommitment,
    CalendarizedDay,
    DailyPlan,
    Food,
    Meal,
    Program,
    WeightLog,
)
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    HOME_VIEWMODE,
)
from notas.presentation.pages.home_calendarization import (
    HomeCalendarizationVM,
    build_home_calendarization_vm,
)
from notas.presentation.viewmodels.base_vm import BaseVM
from notas.presentation.viewmodels.components.header_vm import HeaderVM


@dataclass
class HomeHeroVM:
    title: str
    subtitle: str


@dataclass
class HomeStatVM:
    label: str
    value: int
    icon: str
    url: str


@dataclass
class HomeContentVM:
    header: HeaderVM
    hero: HomeHeroVM
    stats: List[HomeStatVM]
    calendarization: HomeCalendarizationVM
    calendar_progress: dict
    today_date: date
    today_commitments: List[CalendarCommitment]
    month_start: date
    previous_month_key: str
    next_month_key: str
    month_days: list[dict]
    future_plans_count: int
    calendar_coverage: int
    meal_coverage: int
    weight_history: list[WeightLog]
    weight_chart_points: str


@login_required
def home_view(request):
    user = request.user
    today_date = local_date_for_timezone(user.profile.timezone_name or "UTC")
    requested_month = request.GET.get("month", "")
    try:
        month_start = date.fromisoformat(f"{requested_month}-01") if requested_month else today_date.replace(day=1)
    except ValueError:
        month_start = today_date.replace(day=1)
    month_start = month_start.replace(day=1)
    if month_start.year <= 1 or month_start.year >= 9999:
        month_start = today_date.replace(day=1)
    month_grid_start = month_start - timedelta(days=month_start.weekday())
    month_grid_end = month_grid_start + timedelta(days=41)
    month_plans = {
        day.calendar_date: day for day in CalendarizedDay.objects.filter(
            Q(user=user) | Q(user__isnull=True, calendarization__user=user),
            assignment_state=CalendarizedDay.STATE_CURRENT,
            calendar_date__range=(month_grid_start, month_grid_end),
        )
    }
    month_commitments = {}
    for commitment in CalendarCommitment.objects.filter(user=user, calendar_date__range=(month_grid_start, month_grid_end)):
        month_commitments.setdefault(commitment.calendar_date, []).append(commitment)
    month_days = []
    for offset in range(42):
        current_date = month_grid_start + timedelta(days=offset)
        day = month_plans.get(current_date)
        month_days.append({
            "date": current_date,
            "is_current_month": current_date.month == month_start.month,
            "is_today": current_date == today_date,
            "has_plan": bool(day and day.has_plan),
            "commitments": month_commitments.get(current_date, []),
        })
    progress = calendar_adherence_summary(user)
    schedule_summary = calendar_future_schedule_summary(user, today=today_date)
    future_plans_count = schedule_summary["future_plans_count"] or 0
    weight_history = list(WeightLog.objects.filter(user=user).order_by("-date", "-created_at")[:12])
    weight_values = [float(item.weight_kg) for item in reversed(weight_history)]
    weight_min = min(weight_values) if weight_values else 0
    weight_span = max(max(weight_values) - weight_min, 1) if weight_values else 1
    weight_chart_points = " ".join(
        f"{10 + index * 280 / max(len(weight_values) - 1, 1):.1f},{100 - (value - weight_min) * 80 / weight_span:.1f}"
        for index, value in enumerate(weight_values)
    )

    dailyplans_qs = (
        DailyPlan.objects.filter(
            created_by=user,
            is_draft=False,
        )
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .order_by("-created_at")
    )

    meals_qs = Meal.objects.library().filter(
        created_by=user,
        is_draft=False,
    )

    foods_qs = Food.objects.filter(
        created_by=user,
        is_active=True,
    ).order_by("list_order", "name", "id")

    programs_count = Program.objects.filter(created_by=user).count()
    dailyplans_count = dailyplans_qs.count()
    meals_count = meals_qs.count()
    foods_count = foods_qs.count()

    content_vm = HomeContentVM(
        header=build_page_header(
            title="",
            actions=[
                {
                    "key": "profile",
                    "label": "Perfil",
                    "url": reverse("profile_detail"),
                    "method": "get",
                    "icon": "circle-user-round",
                    "order": 10,
                    "desktop_position": "inline",
                    "mobile_position": "inline",
                }
            ],
        ),
        hero=HomeHeroVM(
            title=f"Bienvenido {user.username}!",
            subtitle=(
                "Consulta tu planificación de hoy y organiza tus próximas fechas."
            ),
        ),
        stats=[
            HomeStatVM(
                label="Mis Programas",
                value=programs_count,
                icon="calendar",
                url=reverse("program_list"),
            ),
            HomeStatVM(
                label="Mis Minutas",
                value=dailyplans_count,
                icon="clipboard-list",
                url=reverse("dailyplan_list"),
            ),
            HomeStatVM(
                label="Comidas",
                value=meals_count,
                icon="utensils",
                url=reverse("meal_list"),
            ),
            HomeStatVM(
                label="Alimentos",
                value=foods_count,
                icon="carrot",
                url=reverse("food_list"),
            ),
        ],
        calendarization=build_home_calendarization_vm(user),
        calendar_progress=progress,
        today_date=today_date,
        today_commitments=list(CalendarCommitment.objects.filter(user=user, calendar_date=today_date)),
        month_start=month_start,
        previous_month_key=(month_start - timedelta(days=1)).strftime("%Y-%m"),
        next_month_key=(month_start + timedelta(days=32)).replace(day=1).strftime("%Y-%m"),
        month_days=month_days,
        future_plans_count=future_plans_count,
        calendar_coverage=min(100, round(progress["days_with_plan"] / future_plans_count * 100)) if future_plans_count else 0,
        meal_coverage=min(100, round(progress["completed_meals"] / progress["scheduled_meals"] * 100)) if progress["scheduled_meals"] else 0,
        weight_history=weight_history,
        weight_chart_points=weight_chart_points,
    )

    ui_vm = build_ui_vm(HOME_VIEWMODE)

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/home.html",
        base_vm.as_context(),
    )
