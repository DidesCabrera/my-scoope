from dataclasses import dataclass
from typing import Any

from notas.application.resolvers.meal_food_resolvers import (
    resolve_meal_food_actions,
)
from notas.application.services.nutrition.food_aggregation import (
    build_meal_foods_aggregation,
)
from notas.application.services.nutrition.nutrition_kpis import (
    build_nutrition_kpis_from_dailyplan,
    build_nutrition_kpis_from_meal,
)
from notas.presentation.composition.viewmodel.components.builder_headers import (
    build_dailyplan_meal_header,
)
from notas.presentation.composition.viewmodel.components.builder_table_items import (
    build_mealfood_table_item,
)
from notas.presentation.config.icons import CONTENT_ICON_REGISTRY
from notas.presentation.resolvers.title_resolvers import resolve_category_badge
from notas.application.services.food_imports.localized_names import (
    resolve_food_display_name,
)

@dataclass
class DpmDetailContentData:
    header: Any
    father_card_data: dict
    main_card_data: dict
    child_cards_data: list
    structural_indicators: dict


def build_dpm_detail_content_data(
    dailyplan,
    dpm,
    meal,
    meal_foods,
    user,
    viewmode,
    dailyplan_kpis=None,
    meal_kpis=None,
):
    header = build_dailyplan_meal_header(
        dpm=dpm,
        user=user,
        viewmode=viewmode,
    )

    dailyplan_kpis = dailyplan_kpis or build_nutrition_kpis_from_dailyplan(
        dailyplan,
        user,
    )
    meal_kpis = meal_kpis or build_nutrition_kpis_from_meal(
        meal,
        user,
    )

    dp_total_kcal = dailyplan_kpis["total_kcal"]
    dp_protein = dailyplan_kpis["protein"]
    dp_carbs = dailyplan_kpis["carbs"]
    dp_fat = dailyplan_kpis["fat"]

    dp_kcal_protein = dailyplan_kpis.get("kcal_protein", dp_protein * 4)
    dp_kcal_carbs = dailyplan_kpis.get("kcal_carbs", dp_carbs * 4)
    dp_kcal_fat = dailyplan_kpis.get("kcal_fat", dp_fat * 9)

    dp_alloc = dailyplan_kpis["alloc"]
    father_ppk = dailyplan_kpis["ppk"]

    meal_total_kcal = meal_kpis["total_kcal"]
    meal_protein = meal_kpis["protein"]
    meal_carbs = meal_kpis["carbs"]
    meal_fat = meal_kpis["fat"]

    meal_kcal_protein = meal_kpis.get("kcal_protein", meal_protein * 4)
    meal_kcal_carbs = meal_kpis.get("kcal_carbs", meal_carbs * 4)
    meal_kcal_fat = meal_kpis.get("kcal_fat", meal_fat * 9)

    meal_alloc = meal_kpis["alloc"]
    meal_ppk = meal_kpis["ppk"]

    meal_foods_table_items = [
        build_mealfood_table_item(mf)
        for mf in meal_foods
    ]

    foods_aggregation = build_meal_foods_aggregation(meal)

    structural_indicators = {
        "foods_count": len(meal_foods),
    }

    father_card_data = {
        "father_id": dailyplan.id,
        "title": {
            "name": dailyplan.name,
            "label": "Daily Plan",
            "category": dailyplan.category,
            "category_badge": resolve_category_badge(dailyplan.category),
            "icon": CONTENT_ICON_REGISTRY.get("dailyplan"),
        },
        "rel_id": dpm.id,
        "kpis": {
            "ppk": father_ppk["ppk"],
            "tot_kcal": dp_total_kcal,
            "g_protein": dp_protein,
            "g_carbs": dp_carbs,
            "g_fat": dp_fat,
            "kcal_protein": dp_kcal_protein,
            "kcal_carbs": dp_kcal_carbs,
            "kcal_fat": dp_kcal_fat,
            "alloc_protein": dp_alloc["protein"],
            "alloc_carbs": dp_alloc["carbs"],
            "alloc_fat": dp_alloc["fat"],
        },
        "related_data": {
            "rel_id": dpm.id,
            "hour": str(dpm.hour) if dpm.hour else None,
            "note": dpm.note,
            "alloc_protein": meal_alloc["protein"],
            "alloc_carbs": meal_alloc["carbs"],
            "alloc_fat": meal_alloc["fat"],
        },
    }

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
            "ppk": meal_ppk["ppk"],
            "tot_kcal": meal_total_kcal,
            "g_protein": meal_protein,
            "g_carbs": meal_carbs,
            "g_fat": meal_fat,
            "kcal_protein": meal_kcal_protein,
            "kcal_carbs": meal_kcal_carbs,
            "kcal_fat": meal_kcal_fat,
            "alloc_protein": meal_alloc["protein"],
            "alloc_carbs": meal_alloc["carbs"],
            "alloc_fat": meal_alloc["fat"],
        },
        "table_items": meal_foods_table_items,
        "foods_aggregation": foods_aggregation,
        "metadata": {
            "owner": str(meal.created_by),
            "author": str(meal.original_author),
            "fork_from": str(meal.forked_from) if meal.forked_from else None,
        },
    }

    child_cards_data = []

    for mf in meal_foods:
        food = mf.food
        food_alloc = food.alloc

        child_cards_data.append(
            {
                "child_id": food.id,
                "related_data": {
                    "rel_id": mf.id,
                    "quantity": mf.quantity,
                    "alloc_protein": food_alloc["protein"],
                    "alloc_carbs": food_alloc["carbs"],
                    "alloc_fat": food_alloc["fat"],
                },
                "title": {
                    "name": resolve_food_display_name(food),
                    "label": "Food",
                    "icon": CONTENT_ICON_REGISTRY.get("food"),
                    "category": food.category,
                    "category_badge": resolve_category_badge(food.category),
                },
                "kpis": {
                    "ppk": meal_ppk["ppk"],
                    "tot_kcal": food.total_kcal,
                    "g_protein": food.protein,
                    "g_carbs": food.carbs,
                    "g_fat": food.fat,
                    "kcal_protein": food.kcal_protein,
                    "kcal_carbs": food.kcal_carbs,
                    "kcal_fat": food.kcal_fat,
                    "alloc_protein": food_alloc["protein"],
                    "alloc_carbs": food_alloc["carbs"],
                    "alloc_fat": food_alloc["fat"],
                },
                "actions": resolve_meal_food_actions(
                    mf,
                    user,
                    viewmode,
                ),
            }
        )

    return DpmDetailContentData(
        header=header,
        father_card_data=father_card_data,
        main_card_data=main_card_data,
        child_cards_data=child_cards_data,
        structural_indicators=structural_indicators,
    )