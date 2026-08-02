from dataclasses import dataclass
from typing import Any, List, Optional
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Prefetch
from notas.presentation.pages.object_lookup import get_page_object_or_404

from notas.application.services.nutrition.nutrition_kpis import (
    build_nutrition_kpis_from_dailyplan,
    build_nutrition_kpis_from_meal,
)
from notas.domain.models import DailyPlanMeal, MealFood
from notas.presentation.composition.js.dpm_food_picker_builder import (
    build_dpm_food_picker_context_payload,
)
from notas.presentation.composition.js.food_picker_builder import build_food_picker_foods_payload
from notas.application.queries.food_picker_queries import list_food_picker_items
from notas.presentation.composition.viewmodel.dpm.dpm_content import (
    build_dpm_detail_content_data,
)
from notas.presentation.config.viewmodel_config import (
    DAILYPLAN_MEAL_VIEWMODE_DETAIL,
)
from notas.presentation.navigation.program_context import program_context_query


def _get_dpm_for_user(user, dailyplan_id: int, dpm_id: int):
    return get_page_object_or_404(
        DailyPlanMeal.objects
        .select_related("meal", "dailyplan")
        .prefetch_related(
            "meal__meal_food_set",
            "meal__meal_food_set__food",
            Prefetch(
                "dailyplan__dailyplan_meals",
                queryset=(
                    DailyPlanMeal.objects
                    .select_related("meal")
                    .prefetch_related(
                        "meal__meal_food_set",
                        "meal__meal_food_set__food",
                    )
                ),
            ),
        ),
        id=dpm_id,
        dailyplan_id=dailyplan_id,
        dailyplan__created_by=user,
    )


def _get_optional_editing_mealfood(request_get, meal):
    edit_mf_id = request_get.get("edit_food")
    mealfood = None

    if edit_mf_id:
        mealfood = get_page_object_or_404(
            MealFood,
            pk=edit_mf_id,
            meal=meal,
        )

    return edit_mf_id, mealfood


@dataclass
class DpmDetailPageData:
    dailyplan: Any
    dpm: Any
    meal: Any
    meal_foods: List[Any]
    detail_content_data: Any
    selected_food_id: Optional[str] = None
    editing_mealfood_id: Optional[int] = None
    foods_json: str = "[]"
    food_picker_context_json: str = "{}"
    can_edit_foods: bool = False
    viewmode: Any = None
    program_context_query: str = ""


def get_dpm_detail_page_data(
    user,
    dailyplan_id: int,
    dpm_id: int,
    viewmode,
    request_get=None,
) -> DpmDetailPageData:
    request_get = request_get or {}

    dpm = _get_dpm_for_user(
        user=user,
        dailyplan_id=dailyplan_id,
        dpm_id=dpm_id,
    )

    dailyplan = dpm.dailyplan
    meal = dpm.meal
    meal_foods = list(meal.meal_food_set.select_related("food").all())

    selected_food_id = None
    editing_mealfood_id = None
    foods_json = "[]"
    food_picker_context_json = "{}"
    can_edit_foods = False
    meal_kpis = None
    dailyplan_kpis = None

    if viewmode == DAILYPLAN_MEAL_VIEWMODE_DETAIL:
        can_edit_foods = True
        edit_mf_id, mealfood = _get_optional_editing_mealfood(
            request_get=request_get,
            meal=meal,
        )

        meal_kpis = build_nutrition_kpis_from_meal(
            meal,
            user,
        )

        dailyplan_kpis = build_nutrition_kpis_from_dailyplan(
            dailyplan,
            user,
        )

        food_picker_ctx = build_dpm_food_picker_context_payload(
            meal=meal,
            meal_kpis=meal_kpis,
            dailyplan=dailyplan,
            dailyplan_kpis=dailyplan_kpis,
            mealfood=mealfood,
        )

        selected_food_id = request_get.get("select_food")
        editing_mealfood_id = int(edit_mf_id) if edit_mf_id else None

        food_picker_context_json = json.dumps(
            food_picker_ctx.as_dict(),
            cls=DjangoJSONEncoder,
        )
        foods_json = json.dumps(
            build_food_picker_foods_payload(
                list_food_picker_items(user=user).foods,
            ),
            cls=DjangoJSONEncoder,
        )

    program_context = program_context_query(
        program_day=request_get.get("program_day"),
        dpm=dpm,
    )

    detail_content_data = build_dpm_detail_content_data(
        dailyplan=dailyplan,
        dpm=dpm,
        meal=meal,
        meal_foods=meal_foods,
        user=user,
        viewmode=viewmode,
        dailyplan_kpis=dailyplan_kpis,
        meal_kpis=meal_kpis,
        program_context_query=program_context,
    )

    return DpmDetailPageData(
        dailyplan=dailyplan,
        dpm=dpm,
        meal=meal,
        meal_foods=meal_foods,
        detail_content_data=detail_content_data,
        selected_food_id=selected_food_id,
        editing_mealfood_id=editing_mealfood_id,
        foods_json=foods_json,
        food_picker_context_json=food_picker_context_json,
        can_edit_foods=can_edit_foods,
        viewmode=viewmode,
        program_context_query=program_context,
    )


@dataclass
class DpmEditPageData:
    dailyplan: Any
    dpm: Any
    meal: Any
    meal_foods: List[Any]
    detail_content_data: Any
    viewmode: Any


def get_dpm_edit_page_data(
    user,
    dailyplan_id: int,
    dpm_id: int,
    viewmode,
) -> DpmEditPageData:
    dpm = _get_dpm_for_user(
        user=user,
        dailyplan_id=dailyplan_id,
        dpm_id=dpm_id,
    )

    dailyplan = dpm.dailyplan
    meal = dpm.meal
    meal_foods = list(meal.meal_food_set.select_related("food").all())

    detail_content_data = build_dpm_detail_content_data(
        dailyplan=dailyplan,
        dpm=dpm,
        meal=meal,
        meal_foods=meal_foods,
        user=user,
        viewmode=viewmode,
        dailyplan_kpis=None,
        meal_kpis=None,
    )

    return DpmEditPageData(
        dailyplan=dailyplan,
        dpm=dpm,
        meal=meal,
        meal_foods=meal_foods,
        detail_content_data=detail_content_data,
        viewmode=viewmode,
    )
