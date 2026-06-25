from dataclasses import dataclass
from typing import Any

from notas.domain.models import Food
from notas.presentation.config.viewmodel_config import FOOD_VIEWMODE_PERSONAL_LIST
from notas.presentation.actions.food_resolvers import resolve_food_page_actions


@dataclass
class FoodListPageData:
    foods: Any
    page_actions: list
    viewmode: Any
    list_mode: str = "list"


def _normalize_list_mode(request_get=None):
    mode = (request_get or {}).get("mode", "list")
    return mode if mode in {"list", "reorder", "delete"} else "list"


def get_food_list_page_data(user, request_get=None) -> FoodListPageData:
    list_mode = _normalize_list_mode(request_get)

    foods = (
        Food.objects
        .filter(
            created_by=user,
            is_active=True,
        )
        .select_related(
            "created_by",
        )
        .prefetch_related(
            "localized_names",
        )
        .order_by("list_order", "name", "id")
    )

    viewmode = FOOD_VIEWMODE_PERSONAL_LIST

    page_actions = resolve_food_page_actions(
        user,
        viewmode,
        list_mode=list_mode,
    )

    return FoodListPageData(
        foods=foods,
        page_actions=page_actions,
        viewmode=viewmode,
        list_mode=list_mode,
    )
