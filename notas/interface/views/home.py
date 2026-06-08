from dataclasses import dataclass
from typing import Any, List

from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef, Prefetch
from django.shortcuts import render
from django.urls import reverse

from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    FoodLocalizedName,
    Meal,
    MealFood,
)
from notas.presentation.viewmodels.base_vm import BaseVM
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    HOME_VIEWMODE,
    DAILYPLAN_VIEWMODE_PERSONAL_LIST,
    MEAL_VIEWMODE_PERSONAL_LIST,
    FOOD_VIEWMODE_PERSONAL_LIST,
)

from notas.presentation.composition.viewmodel.dailyplan.dailyplan_content import (
    build_dailyplan_list_content_data,
)

from notas.presentation.composition.viewmodel.meal.meal_content import (
    build_meal_list_content_data,
)

from notas.presentation.composition.viewmodel.dailyplan.list_dailyplan_builder import build_dailyplan_list_vm
from notas.presentation.composition.viewmodel.meal.list_meal_builder import build_meal_list_vm
from notas.presentation.composition.viewmodel.food.list_foods_builder import build_food_list_vm
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
class HomeSectionVM:
    title: str
    subtitle: str
    empty_message: str
    cta_label: str
    cta_url: str
    items: List[Any]


@dataclass
class HomeContentVM:
    header: HeaderVM
    hero: HomeHeroVM
    stats: List[HomeStatVM]
    dailyplans: HomeSectionVM
    meals: HomeSectionVM
    foods: HomeSectionVM


def _primary_display_names_for_home_cards():
    """
    Home renders only a small summary, but the reused card templates need food
    display names. Prefetch only the primary Spanish names to avoid one query
    per food without loading every localized-name row.
    """

    return FoodLocalizedName.objects.filter(
        language="es",
        country__in=["CL", ""],
        is_primary=True,
    ).order_by("country", "name")


def _meal_foods_for_home_cards():
    """
    Keep Home card rendering bounded: MealFood -> Food is useful for the
    embedded summary grids, but localized names are narrowed to the exact rows
    used by resolve_food_display_name().
    """

    return (
        MealFood.objects
        .select_related("food")
        .prefetch_related(
            Prefetch(
                "food__localized_names",
                queryset=_primary_display_names_for_home_cards(),
                to_attr="_prefetched_primary_display_names",
            )
        )
        .order_by("order", "id")
    )


def _dailyplan_meals_for_home_cards():
    return (
        DailyPlanMeal.objects
        .select_related(
            "dailyplan",
            "meal",
            "meal__created_by",
            "meal__original_author",
            "meal__forked_from",
        )
        .prefetch_related(
            Prefetch(
                "meal__meal_food_set",
                queryset=_meal_foods_for_home_cards(),
            )
        )
        .order_by("order", "id")
    )


@login_required
def home_view(request):
    user = request.user

    dailyplans_qs = DailyPlan.objects.filter(created_by=user).order_by("-id")
    meals_qs = (
        Meal.objects
        .filter(created_by=user)
        .annotate(
            is_dpm_instance_sql=Exists(
                DailyPlanMeal.objects.filter(meal_id=OuterRef("pk"))
            )
        )
        .order_by("-id")
    )
    foods_qs = Food.objects.filter(created_by=user).order_by("name")

    dailyplans_count = dailyplans_qs.count()
    meals_count = meals_qs.count()
    foods_count = foods_qs.count()

    recent_dailyplans = list(
        dailyplans_qs
        .select_related("created_by", "original_author", "forked_from")
        .prefetch_related(
            "shares",
            Prefetch(
                "dailyplan_meals",
                queryset=_dailyplan_meals_for_home_cards(),
            ),
        )[:3]
    )
    recent_meals = list(
        meals_qs
        .select_related("created_by", "original_author", "forked_from")
        .prefetch_related(
            Prefetch(
                "meal_food_set",
                queryset=_meal_foods_for_home_cards(),
            ),
        )[:3]
    )
    recent_foods = list(
        foods_qs
        .select_related("created_by")[:8]
    )

    dailyplan_content_data = build_dailyplan_list_content_data(
        recent_dailyplans,
        user,
        DAILYPLAN_VIEWMODE_PERSONAL_LIST,
    )
    dailyplans_vm = build_dailyplan_list_vm(dailyplan_content_data)

    meal_content_data = build_meal_list_content_data(
        recent_meals,
        user,
        MEAL_VIEWMODE_PERSONAL_LIST,
    )
    meals_vm = build_meal_list_vm(meal_content_data)

    foods_vm = build_food_list_vm(
        recent_foods,
        user,
        FOOD_VIEWMODE_PERSONAL_LIST,
    )

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
        ],
        dailyplans=HomeSectionVM(
            title="Resumen de DailyPlans",
            subtitle="Tus planes más recientes y su estructura nutricional.",
            empty_message="Aún no tienes planes diarios creados.",
            cta_label="Ver todos los planes",
            cta_url=reverse("dailyplan_list"),
            items=dailyplans_vm.child_cards,
        ),
        meals=HomeSectionVM(
            title="Resumen de Meals",
            subtitle="Tus comidas reutilizables más recientes.",
            empty_message="Aún no tienes meals creadas.",
            cta_label="Ver todas las meals",
            cta_url=reverse("meal_list"),
            items=meals_vm.child_cards,
        ),
        foods=HomeSectionVM(
            title="Resumen de Foods",
            subtitle="Tu base de alimentos disponible.",
            empty_message="Aún no tienes foods creados.",
            cta_label="Ver todos los alimentos",
            cta_url=reverse("food_list"),
            items=foods_vm.items,
        ),
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
