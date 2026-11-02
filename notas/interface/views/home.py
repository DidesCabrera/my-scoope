from dataclasses import dataclass
from datetime import date
from typing import List

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

from notas.application.queries.calendar_metrics import calendar_adherence_summary
from notas.application.services.calendarization.scheduling import local_date_for_timezone
from notas.domain.models import (
    CalendarCommitment,
    DailyPlan,
    Food,
    Meal,
    Program,
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


@login_required
def home_view(request):
    user = request.user
    today_date = local_date_for_timezone(user.profile.timezone_name or "UTC")

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
        calendar_progress=calendar_adherence_summary(user),
        today_date=today_date,
        today_commitments=list(CalendarCommitment.objects.filter(user=user, calendar_date=today_date)),
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
