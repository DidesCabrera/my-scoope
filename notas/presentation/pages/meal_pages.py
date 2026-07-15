from dataclasses import dataclass
from typing import Any, List, Optional
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import BooleanField, Prefetch, Value
from notas.presentation.pages.object_lookup import get_page_object_or_404

from notas.presentation.actions.meal_resolvers import (
    resolve_meal_page_actions,
)
from notas.application.services.access.access import get_meal_for_user
from notas.application.services.nutrition.nutrition_kpis import (
    build_nutrition_kpis_from_meal,
)
from notas.domain.models import FoodLocalizedName, Meal, MealFood
from notas.presentation.composition.js.food_picker_builder import (
    build_food_picker_context_payload,
    build_food_picker_foods_payload,
)
from notas.application.queries.food_picker_queries import list_food_picker_items
from notas.presentation.viewmodels.meals import (
    build_meal_detail_content_data,
    build_meal_list_content_data,
)
from notas.presentation.config.viewmodel_config import (
    MEAL_VIEWMODE_DRAFT_LIST,
    MEAL_VIEWMODE_EXPLORE_LIST,
    MEAL_VIEWMODE_PERSONAL_DETAIL,
    MEAL_VIEWMODE_PERSONAL_EDIT_FROM_DAILYPLAN,
    MEAL_VIEWMODE_PERSONAL_LIST,
    MEAL_VIEWMODE_SHARED_LIST,
)




def _standalone_meals_queryset():
    return Meal.objects.annotate(
        is_dpm_instance_sql=Value(False, output_field=BooleanField()),
    )


def _meal_foods_for_card_rendering():
    """
    Lightweight prefetch queryset for list/detail cards.

    It keeps the useful MealFood -> Food join, but only prefetches the
    localized display-name rows that the UI can actually use. This avoids
    both extremes: N+1 localized-name queries and loading every localized
    name for every food in broad list pages.
    """

    primary_display_names = FoodLocalizedName.objects.filter(
        language="es",
        country__in=["CL", ""],
        is_primary=True,
    ).order_by("country", "name")

    return (
        MealFood.objects
        .select_related("food")
        .prefetch_related(
            Prefetch(
                "food__localized_names",
                queryset=primary_display_names,
                to_attr="_prefetched_primary_display_names",
            ),
        )
        .order_by("order", "id")
    )

@dataclass
class MealDetailPageData:
    meal: Any
    meal_foods: List[Any]
    detail_content_data: Any
    selected_food_id: Optional[str] = None
    editing_mealfood_id: Optional[int] = None
    foods_json: str = "[]"
    food_picker_context_json: str = "{}"
    can_edit_foods: bool = False
    show_return_to_dailyplan: bool = False
    viewmode: Any = None


@dataclass
class MealListPageData:
    meals: Any
    list_content_data: Any
    page_actions: list
    viewmode: Any
    list_mode: str = "list"


def get_meal_detail_page_data(
    user,
    meal_id: int,
    viewmode,
    request_get=None,
) -> MealDetailPageData:
    request_get = request_get or {}

    meal = (
        Meal.objects
        .prefetch_related(
            Prefetch(
                "meal_food_set",
                queryset=_meal_foods_for_card_rendering(),
            ),
        )
        .get(pk=meal_id)
    )

    meal_foods = list(meal.meal_food_set.all())

    selected_food_id = None
    editing_mealfood_id = None
    foods_json = "[]"
    food_picker_context_json = "{}"
    show_return_to_dailyplan = False
    can_edit_foods = False

    effective_viewmode = viewmode

    if viewmode == MEAL_VIEWMODE_PERSONAL_DETAIL and meal.created_by == user:
        can_edit_foods = True
        edit_mf_id = request_get.get("edit_food")
        mealfood = None

        if edit_mf_id:
            mealfood = get_page_object_or_404(
                MealFood,
                pk=edit_mf_id,
                meal=meal,
            )

        nutrition_kpis = build_nutrition_kpis_from_meal(
            meal,
            user,
        )

        food_picker_ctx = build_food_picker_context_payload(
            meal=meal,
            nutrition_kpis=nutrition_kpis,
            mealfood=mealfood,
        )

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

        selected_food_id = request_get.get("select_food")
        editing_mealfood_id = int(edit_mf_id) if edit_mf_id else None
        show_return_to_dailyplan = (
            meal.pending_dailyplan is not None
            and not meal.is_draft
        )

        if meal.pending_dailyplan:
            effective_viewmode = MEAL_VIEWMODE_PERSONAL_EDIT_FROM_DAILYPLAN
        else:
            effective_viewmode = MEAL_VIEWMODE_PERSONAL_DETAIL

    else:
        meal = get_meal_for_user(user, meal_id)

    detail_content_data = build_meal_detail_content_data(
        meal=meal,
        user=user,
        viewmode=effective_viewmode,
    )

    return MealDetailPageData(
        meal=meal,
        meal_foods=meal_foods,
        detail_content_data=detail_content_data,
        selected_food_id=selected_food_id,
        editing_mealfood_id=editing_mealfood_id,
        foods_json=foods_json,
        food_picker_context_json=food_picker_context_json,
        can_edit_foods=can_edit_foods,
        show_return_to_dailyplan=show_return_to_dailyplan,
        viewmode=effective_viewmode,
    )


def _normalize_list_mode(request_get=None):
    mode = (request_get or {}).get("mode", "list")
    return mode if mode in {"list", "reorder", "delete"} else "list"


def get_meal_list_page_data(user, request_get=None) -> MealListPageData:
    list_mode = _normalize_list_mode(request_get)

    if list_mode in {"reorder", "delete"}:
        meals = (
            _standalone_meals_queryset()
            .filter(
                created_by=user,
                is_draft=False,
                dailyplanmeal__isnull=True,
            )
            .only("id", "name", "list_order", "created_at")
            .order_by("list_order", "-created_at", "-id")
            .distinct()
        )
    else:
        meals = (
            _standalone_meals_queryset()
            .filter(
                created_by=user,
                is_draft=False,
                dailyplanmeal__isnull=True,
            )
            .select_related("created_by", "original_author", "forked_from")
            .prefetch_related(
                Prefetch(
                    "meal_food_set",
                    queryset=_meal_foods_for_card_rendering(),
                ),
            )
            .order_by("list_order", "-created_at", "-id")
            .distinct()
        )

    viewmode = MEAL_VIEWMODE_PERSONAL_LIST

    list_content_data = build_meal_list_content_data(
        meals=meals,
        user=user,
        viewmode=viewmode,
        list_mode=list_mode,
    )

    page_actions = resolve_meal_page_actions(
        user,
        viewmode,
        list_mode=list_mode,
    )

    return MealListPageData(
        meals=meals,
        list_content_data=list_content_data,
        page_actions=page_actions,
        viewmode=viewmode,
        list_mode=list_mode,
    )


def get_meal_explore_list_page_data(user) -> MealListPageData:
    meals = (
        _standalone_meals_queryset()
        .filter(
            is_public=True,
            is_draft=False,
            dailyplanmeal__isnull=True,
        )
        .select_related("created_by", "original_author", "forked_from")
        .prefetch_related(
            Prefetch(
                "meal_food_set",
                queryset=_meal_foods_for_card_rendering(),
            ),
        )
        .order_by("-created_at")
        .distinct()
    )

    viewmode = MEAL_VIEWMODE_EXPLORE_LIST

    list_content_data = build_meal_list_content_data(
        meals=meals,
        user=user,
        viewmode=viewmode,
    )

    page_actions = resolve_meal_page_actions(
        user,
        viewmode,
    )

    return MealListPageData(
        meals=meals,
        list_content_data=list_content_data,
        page_actions=page_actions,
        viewmode=viewmode,
    )


def get_meal_shared_list_page_data(user) -> MealListPageData:
    meals = (
        _standalone_meals_queryset()
        .filter(
            shares__accepted_by=user,
            shares__removed=False,
            is_draft=False,
            dailyplanmeal__isnull=True,
        )
        .select_related("created_by", "original_author", "forked_from")
        .prefetch_related(
            "shares",
            Prefetch(
                "meal_food_set",
                queryset=_meal_foods_for_card_rendering(),
            ),
        )
        .distinct()
    )

    viewmode = MEAL_VIEWMODE_SHARED_LIST

    list_content_data = build_meal_list_content_data(
        meals=meals,
        user=user,
        viewmode=viewmode,
    )

    page_actions = resolve_meal_page_actions(
        user,
        viewmode,
    )

    return MealListPageData(
        meals=meals,
        list_content_data=list_content_data,
        page_actions=page_actions,
        viewmode=viewmode,
    )


def get_meal_draft_list_page_data(user) -> MealListPageData:
    meals = (
        _standalone_meals_queryset()
        .filter(
            created_by=user,
            is_draft=True,
            dailyplanmeal__isnull=True,
        )
        .select_related("created_by", "original_author", "forked_from")
        .prefetch_related(
            Prefetch(
                "meal_food_set",
                queryset=_meal_foods_for_card_rendering(),
            ),
        )
        .order_by("-created_at")
        .distinct()
    )

    viewmode = MEAL_VIEWMODE_DRAFT_LIST

    list_content_data = build_meal_list_content_data(
        meals=meals,
        user=user,
        viewmode=viewmode,
    )

    page_actions = resolve_meal_page_actions(
        user,
        viewmode,
    )

    return MealListPageData(
        meals=meals,
        list_content_data=list_content_data,
        page_actions=page_actions,
        viewmode=viewmode,
    )