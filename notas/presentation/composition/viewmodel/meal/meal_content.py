# notas/presentation/composition/viewmodel/meal/meal_content.py

from dataclasses import dataclass
from typing import Any

from notas.application.services.food_imports.localized_names import (
    resolve_food_display_name,
)
from notas.application.services.nutrition.food_aggregation import (
    build_meal_foods_aggregation,
)
from notas.application.services.nutrition.nutrition_kpis import get_ppk_meal
from notas.presentation.actions.meal_food_resolvers import (
    resolve_meal_food_actions,
)
from notas.presentation.actions.meal_resolvers import (
    resolve_meal_entity_actions,
)
from notas.presentation.composition.viewmodel.components.builder_headers import (
    build_meal_header,
)
from notas.presentation.composition.viewmodel.components.builder_table_items import (
    build_mealfood_table_item,
)
from notas.presentation.config.icons import CONTENT_ICON_REGISTRY
from notas.presentation.resolvers.title_resolvers import resolve_category_badge


@dataclass
class MealDetailContentData:
    header: Any
    main_card_data: dict
    structural_indicators: dict
    table_items: list
    child_cards_data: list


@dataclass
class MealListContentData:
    child_cards_data: list


def build_meal_detail_content_data(
    meal,
    user,
    viewmode,
):
    header = build_meal_header(
        meal=meal,
        user=user,
        viewmode=viewmode,
    )

    meal_total_kcal = meal.total_kcal_cached or meal.total_kcal
    meal_protein = meal.protein_cached or meal.protein
    meal_carbs = meal.carbs_cached or meal.carbs
    meal_fat = meal.fat_cached or meal.fat

    meal_alloc = {
        "protein": meal.alloc_protein_cached or meal.alloc["protein"],
        "carbs": meal.alloc_carbs_cached or meal.alloc["carbs"],
        "fat": meal.alloc_fat_cached or meal.alloc["fat"],
    }

    ppk = get_ppk_meal(meal, user)

    # Use the page-level prefetch cache when available. Calling
    # select_related() here would create a new queryset and bypass the
    # prefetched MealFood/Food/localized-name data.
    meal_foods = list(meal.meal_food_set.all())

    table_items = [
        build_mealfood_table_item(mf)
        for mf in meal_foods
    ]

    foods_aggregation = build_meal_foods_aggregation(meal)

    main_card_data = {
        "main_id": meal.id,
        "title": {
            "name": meal.name,
            "label": "Meal",
            "icon": CONTENT_ICON_REGISTRY.get("meal"),
            "category": meal.category,
            "category_badge": resolve_category_badge(meal.category),
            "foods_count": len(foods_aggregation),
        },
        "kpis": {
            "ppk": ppk["ppk"],
            "tot_kcal": meal_total_kcal,
            "g_protein": meal_protein,
            "g_carbs": meal_carbs,
            "g_fat": meal_fat,
            "kcal_protein": meal.kcal_protein_cached or meal.kcal_protein,
            "kcal_carbs": meal.kcal_carbs_cached or meal.kcal_carbs,
            "kcal_fat": meal.kcal_fat_cached or meal.kcal_fat,
            "alloc_protein": meal_alloc["protein"],
            "alloc_carbs": meal_alloc["carbs"],
            "alloc_fat": meal_alloc["fat"],
        },
        "foods_aggregation": foods_aggregation,
        "metadata": {
            "owner": str(meal.created_by),
            "author": str(meal.original_author),
            "fork_from": str(meal.forked_from) if meal.forked_from else None,
        },
        "show_kpis": len(meal_foods) > 0,
        "show_table": len(meal_foods) > 0,
    }

    structural_indicators = {
        "foods_count": len(meal_foods),
    }

    child_cards_data = []

    for mf in meal_foods:
        food = mf.food

        qty_factor = float(mf.quantity) / 100.0

        food_total_kcal = float(food.total_kcal) * qty_factor
        food_protein = float(food.protein) * qty_factor
        food_carbs = float(food.carbs) * qty_factor
        food_fat = float(food.fat) * qty_factor

        food_alloc = food.alloc

        child_cards_data.append(
            {
                "child_id": food.id,
                "related_data": {
                    "rel_id": mf.id,
                    "quantity": float(mf.quantity),
                    "alloc_protein": float(food_alloc["protein"]),
                    "alloc_carbs": float(food_alloc["carbs"]),
                    "alloc_fat": float(food_alloc["fat"]),
                },
                "title": {
                    "name": resolve_food_display_name(food),
                    "label": "Food",
                    "icon": CONTENT_ICON_REGISTRY.get("food"),
                    "category": getattr(food, "category", None),
                    "category_badge": resolve_category_badge(
                        getattr(food, "category", None)
                    ),
                },
                "kpis": {
                    "ppk": 0,
                    "tot_kcal": food_total_kcal,
                    "g_protein": food_protein,
                    "g_carbs": food_carbs,
                    "g_fat": food_fat,
                    "kcal_protein": food_protein * 4,
                    "kcal_carbs": food_carbs * 4,
                    "kcal_fat": food_fat * 9,
                    "alloc_protein": float(food_alloc["protein"]),
                    "alloc_carbs": float(food_alloc["carbs"]),
                    "alloc_fat": float(food_alloc["fat"]),
                },
                "actions": resolve_meal_food_actions(
                    mf,
                    user,
                    viewmode,
                ),
            }
        )

    return MealDetailContentData(
        header=header,
        main_card_data=main_card_data,
        structural_indicators=structural_indicators,
        table_items=table_items,
        child_cards_data=child_cards_data,
    )


def build_meal_list_content_data(meals, user, viewmode, list_mode="list"):
    child_cards_data = []

    if list_mode in {"reorder", "delete"}:
        return MealListContentData(
            child_cards_data=[
                {
                    "child_id": meal.id,
                    "title": {"name": meal.name},
                }
                for meal in meals
            ]
        )

    for meal in meals:
        meal_total_kcal = meal.total_kcal_cached or meal.total_kcal
        meal_protein = meal.protein_cached or meal.protein
        meal_carbs = meal.carbs_cached or meal.carbs
        meal_fat = meal.fat_cached or meal.fat

        meal_alloc = {
            "protein": meal.alloc_protein_cached or meal.alloc["protein"],
            "carbs": meal.alloc_carbs_cached or meal.alloc["carbs"],
            "fat": meal.alloc_fat_cached or meal.alloc["fat"],
        }

        ppk = get_ppk_meal(meal, user)

        meal_foods = list(meal.meal_food_set.all())

        table_items = [
            build_mealfood_table_item(mf)
            for mf in meal_foods
        ]

        foods_count = len(meal.foods_aggregation_cached or meal_foods)

        actions = resolve_meal_entity_actions(
            meal,
            user,
            viewmode,
        )

        child_cards_data.append(
            {
                "child_id": meal.id,
                "title": {
                    "name": meal.name,
                    "label": "Meal",
                    "icon": CONTENT_ICON_REGISTRY.get("meal"),
                    "category": meal.category,
                    "category_badge": resolve_category_badge(meal.category),
                    "foods_count": foods_count,
                },
                "kpis": {
                    "ppk": ppk["ppk"],
                    "tot_kcal": meal_total_kcal,
                    "g_protein": meal_protein,
                    "g_carbs": meal_carbs,
                    "g_fat": meal_fat,
                    "kcal_protein": meal.kcal_protein_cached or meal.kcal_protein,
                    "kcal_carbs": meal.kcal_carbs_cached or meal.kcal_carbs,
                    "kcal_fat": meal.kcal_fat_cached or meal.kcal_fat,
                    "alloc_protein": meal_alloc["protein"],
                    "alloc_carbs": meal_alloc["carbs"],
                    "alloc_fat": meal_alloc["fat"],
                },
                "table_items": table_items,
                "foods_aggregation": [],
                "metadata": {
                    "owner": str(meal.created_by),
                    "author": str(meal.original_author),
                    "fork_from": str(meal.forked_from) if meal.forked_from else None,
                },
                "actions": actions,
            }
        )

    return MealListContentData(
        child_cards_data=child_cards_data,
    )