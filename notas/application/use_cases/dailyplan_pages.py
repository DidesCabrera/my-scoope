from dataclasses import dataclass
from typing import Optional, List, Any
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import get_object_or_404

from notas.domain.models import DailyPlan, DailyPlanMeal, Meal
from notas.application.services.queries.dailyplan_queries import (
    dailyplans_with_kcal,
    get_dailyplan_for_edit,
    get_dailyplan_meals_with_foods,
)
from notas.application.services.queries.meal_queries import meals_with_kcal
from notas.application.services.nutrition.nutrition_kpis import (
    build_nutrition_kpis_from_dailyplan,
)
from notas.application.services.nutrition.meal_nutrition import rebuild_meal_cached_state
from notas.presentation.composition.js.meal_picker_builder import (
    build_meal_picker_context_payload,
    build_meal_picker_data_payload,
)
from notas.presentation.config.viewmodel_config import (
    DAILYPLAN_VIEWMODE_PERSONAL_LIST,
    DAILYPLAN_VIEWMODE_EXPLORE_LIST,
    DAILYPLAN_VIEWMODE_SHARED_LIST,
    DAILYPLAN_VIEWMODE_DRAFT_LIST,
    DAILYPLAN_VIEWMODE_PERSONAL_DETAIL,
)
from notas.application.services.access.access import get_dailyplan_for_user

from notas.application.resolvers.dailyplan_resolvers import (
    resolve_dailyplan_page_actions,
)

from notas.presentation.composition.viewmodel.dailyplan.dailyplan_content import (
    build_dailyplan_detail_content_data,
    build_dailyplan_list_content_data,
)




def _meal_cache_is_missing(meal: Meal) -> bool:
    return any(
        value is None
        for value in [
            meal.protein_cached,
            meal.carbs_cached,
            meal.fat_cached,
            meal.total_kcal_cached,
            meal.alloc_protein_cached,
            meal.alloc_carbs_cached,
            meal.alloc_fat_cached,
            meal.foods_aggregation_cached,
        ]
    )


def _ensure_cached_state(meals):
    """
    Rehidrata cache solo si la meal tiene foods y su cache está incompleto.
    Evita que el picker use macros 0/null cuando la meal sí tiene contenido.
    """
    result = []

    for meal in meals:
        if meal.meal_food_set.exists() and _meal_cache_is_missing(meal):
            rebuild_meal_cached_state(meal)
            meal.refresh_from_db()

        result.append(meal)

    return result


@dataclass
class DailyPlanDetailPageData:
    dailyplan: Any
    dailyplan_meals: List[Any]
    detail_content_data: Any
    selected_meal_id: Optional[str] = None
    editing_dailyplanmeal_id: Optional[int] = None
    meal_picker_data_json: str = "{}"
    meal_picker_context_json: str = "{}"
    viewmode: Any = None



@dataclass
class DailyPlanListPageData:
    dailyplans: Any
    list_content_data: Any
    page_actions: list
    viewmode: Any
    list_mode: str = "list"


def get_dailyplan_detail_page_data(
    user,
    dailyplan_id: int,
    viewmode,
    request_get=None,
) -> DailyPlanDetailPageData:
    request_get = request_get or {}

    selected_meal_id = None
    editing_dailyplanmeal_id = None
    meal_picker_data_json = "{}"
    meal_picker_context_json = "{}"
    effective_viewmode = viewmode

    if viewmode == DAILYPLAN_VIEWMODE_PERSONAL_DETAIL:
        dailyplan = get_dailyplan_for_edit(user, dailyplan_id)
        dailyplan_meals = get_dailyplan_meals_with_foods(dailyplan)

        edit_dpm_id = request_get.get("edit_meal")
        selected_meal_id = request_get.get("select_meal")

        dpm = None
        if edit_dpm_id:
            dpm = get_object_or_404(
                DailyPlanMeal.objects.select_related("meal"),
                pk=edit_dpm_id,
                dailyplan=dailyplan,
            )

        browse_meals_qs = (
            meals_with_kcal()
            .filter(
                created_by=user,
                is_draft=False,
                dailyplanmeal__isnull=True,
            )
            .order_by("-created_at")
            .distinct()
        )

        existing_meals_qs = (
            meals_with_kcal()
            .filter(
                dailyplanmeal__dailyplan=dailyplan,
            )
            .distinct()
        )

        browse_meals = _ensure_cached_state(list(browse_meals_qs))
        existing_meals = _ensure_cached_state(list(existing_meals_qs))

        dailyplan_kpis = build_nutrition_kpis_from_dailyplan(
            dailyplan,
            user,
        )

        meal_picker_data = build_meal_picker_data_payload(
            browse_meals_qs=browse_meals,
            existing_meals_qs=existing_meals,
            current_weight=dailyplan_kpis.get("weight"),
        )

        meal_picker_context = build_meal_picker_context_payload(
            dailyplan=dailyplan,
            dailyplan_kpis=dailyplan_kpis,
            dpm=dpm,
        )

        meal_picker_data_json = json.dumps(
            meal_picker_data,
            cls=DjangoJSONEncoder,
        )

        meal_picker_context_json = json.dumps(
            meal_picker_context.as_dict(),
            cls=DjangoJSONEncoder,
        )

        editing_dailyplanmeal_id = int(edit_dpm_id) if edit_dpm_id else None
        effective_viewmode = DAILYPLAN_VIEWMODE_PERSONAL_DETAIL

    else:
        dailyplan = get_dailyplan_for_user(user, dailyplan_id)
        dailyplan_meals = get_dailyplan_meals_with_foods(dailyplan)

    detail_content_data = build_dailyplan_detail_content_data(
        dailyplan=dailyplan,
        dailyplan_meals=dailyplan_meals,
        user=user,
        viewmode=effective_viewmode,
    )

    return DailyPlanDetailPageData(
        dailyplan=dailyplan,
        dailyplan_meals=dailyplan_meals,
        detail_content_data=detail_content_data,
        selected_meal_id=selected_meal_id,
        editing_dailyplanmeal_id=editing_dailyplanmeal_id,
        meal_picker_data_json=meal_picker_data_json,
        meal_picker_context_json=meal_picker_context_json,
        viewmode=effective_viewmode,
    )


def _normalize_list_mode(request_get=None):
    mode = (request_get or {}).get("mode", "list")
    return mode if mode in {"list", "reorder", "delete"} else "list"


def get_dailyplan_list_page_data(user, request_get=None) -> DailyPlanListPageData:
    list_mode = _normalize_list_mode(request_get)

    dailyplans = (
        dailyplans_with_kcal()
        .filter(
            created_by=user,
            is_draft=False,
        )
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .order_by("list_order", "-created_at", "-id")
    )

    viewmode = DAILYPLAN_VIEWMODE_PERSONAL_LIST

    list_content_data = build_dailyplan_list_content_data(
        dailyplans=dailyplans,
        user=user,
        viewmode=viewmode,
    )

    page_actions = resolve_dailyplan_page_actions(
        user,
        viewmode,
        list_mode=list_mode,
    )

    return DailyPlanListPageData(
        dailyplans=dailyplans,
        list_content_data=list_content_data,
        page_actions=page_actions,
        viewmode=viewmode,
        list_mode=list_mode,
    )


def get_dailyplan_explore_list_page_data(user) -> DailyPlanListPageData:
    dailyplans = (
        dailyplans_with_kcal()
        .filter(
            is_public=True,
            is_draft=False,
        )
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .order_by("-created_at")
    )

    viewmode = DAILYPLAN_VIEWMODE_EXPLORE_LIST

    list_content_data = build_dailyplan_list_content_data(
        dailyplans=dailyplans,
        user=user,
        viewmode=viewmode,
    )

    page_actions = resolve_dailyplan_page_actions(
        user,
        viewmode,
    )

    return DailyPlanListPageData(
        dailyplans=dailyplans,
        list_content_data=list_content_data,
        page_actions=page_actions,
        viewmode=viewmode,
    )


def get_dailyplan_shared_list_page_data(user) -> DailyPlanListPageData:
    dailyplans = (
        dailyplans_with_kcal()
        .filter(
            shares__accepted_by=user,
            shares__removed=False,
            is_draft=False,
        )
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .prefetch_related("shares")
        .distinct()
    )

    viewmode = DAILYPLAN_VIEWMODE_SHARED_LIST

    list_content_data = build_dailyplan_list_content_data(
        dailyplans=dailyplans,
        user=user,
        viewmode=viewmode,
    )

    page_actions = resolve_dailyplan_page_actions(
        user,
        viewmode,
    )

    return DailyPlanListPageData(
        dailyplans=dailyplans,
        list_content_data=list_content_data,
        page_actions=page_actions,
        viewmode=viewmode,
    )


def get_dailyplan_draft_list_page_data(user) -> DailyPlanListPageData:
    dailyplans = (
        dailyplans_with_kcal()
        .filter(
            created_by=user,
            is_draft=True,
        )
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .order_by("-created_at")
    )

    viewmode = DAILYPLAN_VIEWMODE_DRAFT_LIST

    list_content_data = build_dailyplan_list_content_data(
        dailyplans=dailyplans,
        user=user,
        viewmode=viewmode,
    )

    page_actions = resolve_dailyplan_page_actions(
        user,
        viewmode,
    )

    return DailyPlanListPageData(
        dailyplans=dailyplans,
        list_content_data=list_content_data,
        page_actions=page_actions,
        viewmode=viewmode,
    )


