from dataclasses import dataclass
from typing import List

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

from notas.domain.models import (
    DailyPlan,
    Food,
    Meal,
)
from notas.presentation.viewmodels.base_vm import BaseVM
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    HOME_VIEWMODE,
)

from notas.presentation.viewmodels.components.header_vm import HeaderVM

from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header


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



@login_required
def home_view(request):
    user = request.user

    dailyplans_qs = (
        DailyPlan.objects
        .filter(
            created_by=user,
            is_draft=False,
        )
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .order_by("-created_at")
    )

    meals_qs = (
        Meal.objects
        .filter(
            created_by=user,
            is_draft=False,
            dailyplanmeal__isnull=True,
        )
        .distinct()
    )

    foods_qs = (
        Food.objects
        .filter(
            created_by=user,
            is_active=True,
        )
        .order_by("list_order", "name", "id")
    )

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
                "Organiza planes diarios, comidas y alimentos en un solo lugar. "
                "Este es tu resumen de trabajo actual."
            ),
        ),
        stats=[
            HomeStatVM(
                label="Planes Diarios",
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
        ]
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
