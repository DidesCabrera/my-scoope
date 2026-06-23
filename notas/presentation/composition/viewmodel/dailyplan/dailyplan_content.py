# notas/presentation/composition/viewmodel/dailyplan/dailyplan_content.py

from dataclasses import dataclass
from typing import Any

from django.urls import reverse

from notas.application.resolvers.dailyplan_meal_resolvers import (
    resolve_dailyplan_meal_actions,
)
from notas.application.resolvers.dailyplan_resolvers import (
    resolve_dailyplan_entity_actions,
)
from notas.application.resolvers.share_resolvers import resolve_share_actions
from notas.application.services.cache.dailyplan_summary import get_dailyplan_summary
from notas.application.services.nutrition.food_aggregation import (
    build_dailyplan_foods_aggregation,
    build_meal_foods_aggregation,
)
from notas.application.services.nutrition.nutrition_kpis import (
    get_ppk_meal,
)
from notas.application.services.nutrition.weight import get_current_weight
from notas.presentation.composition.viewmodel.components.builder_headers import (
    build_dailyplan_header,
)
from notas.presentation.composition.viewmodel.components.builder_menu import (
    build_dailyplan_menu,
)
from notas.presentation.composition.viewmodel.components.builder_table_items import (
    build_dailyplan_food_aggregation_table_item,
    build_dailyplanmeal_table_item,
    build_mealfood_table_item,
)
from notas.presentation.config.icons import CONTENT_ICON_REGISTRY
from notas.presentation.config.viewmodel_config import DAILYPLAN_VIEWMODE_PERSONAL_DETAIL
from notas.presentation.resolvers.title_resolvers import resolve_category_badge


def _cached_or_live(obj, cached_attr, live_attr):
    cached_value = getattr(obj, cached_attr, None)
    return cached_value if cached_value is not None else getattr(obj, live_attr)


def _dailyplan_meals_for_list_card(dailyplan):
    """
    Reuse a page-level prefetch when available. dailyplan.meals_with_foods()
    creates a new queryset, so calling it after Home already prefetched recent
    cards would do the same work again.
    """

    prefetched = getattr(dailyplan, "_prefetched_objects_cache", {}).get(
        "dailyplan_meals"
    )

    if prefetched is not None:
        return list(prefetched)

    return list(dailyplan.meals_with_foods())


def _dailyplan_list_nutrition_snapshot(dailyplan, dailyplan_meals):
    """
    Build list-card totals in one pass over the meals.

    The DailyPlan model properties are correct, but each property walks the
    relation again. Home and list cards need the full KPI group, so a single
    snapshot avoids repeated iteration and falls back to live values only when
    a meal cache is missing.
    """

    totals = {
        "protein": 0,
        "carbs": 0,
        "fat": 0,
        "kcal_protein": 0,
        "kcal_carbs": 0,
        "kcal_fat": 0,
    }

    for dpm in dailyplan_meals:
        meal = dpm.meal
        totals["protein"] += _cached_or_live(meal, "protein_cached", "protein")
        totals["carbs"] += _cached_or_live(meal, "carbs_cached", "carbs")
        totals["fat"] += _cached_or_live(meal, "fat_cached", "fat")
        totals["kcal_protein"] += _cached_or_live(
            meal,
            "kcal_protein_cached",
            "kcal_protein",
        )
        totals["kcal_carbs"] += _cached_or_live(
            meal,
            "kcal_carbs_cached",
            "kcal_carbs",
        )
        totals["kcal_fat"] += _cached_or_live(
            meal,
            "kcal_fat_cached",
            "kcal_fat",
        )

    total_kcal = (
        totals["kcal_protein"]
        + totals["kcal_carbs"]
        + totals["kcal_fat"]
    )

    if total_kcal > 0:
        alloc = {
            "protein": totals["kcal_protein"] / total_kcal * 100,
            "carbs": totals["kcal_carbs"] / total_kcal * 100,
            "fat": totals["kcal_fat"] / total_kcal * 100,
        }
    else:
        alloc = {"protein": 0, "carbs": 0, "fat": 0}

    return {
        **totals,
        "total_kcal": total_kcal,
        "alloc": alloc,
    }


@dataclass
class DailyPlanDetailContentData:
    header: Any
    main_card_data: dict
    child_cards_data: list
    foods_aggregation: Any
    foods_aggregation_table: list
    structural_indicators: dict


@dataclass
class DailyPlanListContentData:
    child_cards_data: list


def build_dailyplan_detail_content_data(
    dailyplan,
    dailyplan_meals,
    user,
    viewmode,
):
    header = build_dailyplan_header(
        dailyplan=dailyplan,
        user=user,
        viewmode=viewmode,
    )

    summary = get_dailyplan_summary(dailyplan)
    nutrition_snapshot = summary.get("totals", {})

    dp_total_kcal = nutrition_snapshot.get("total_kcal", 0)
    dp_protein = nutrition_snapshot.get("protein", 0)
    dp_carbs = nutrition_snapshot.get("carbs", 0)
    dp_fat = nutrition_snapshot.get("fat", 0)
    dp_kcal_protein = nutrition_snapshot.get("kcal_protein", 0)
    dp_kcal_carbs = nutrition_snapshot.get("kcal_carbs", 0)
    dp_kcal_fat = nutrition_snapshot.get("kcal_fat", 0)
    dp_alloc = nutrition_snapshot.get("alloc", {"protein": 0, "carbs": 0, "fat": 0})

    foods_aggregation = build_dailyplan_foods_aggregation(dailyplan_meals)
    foods_aggregation_table = summary.get("foods_aggregation_table", [])

    structural_indicators = {
        "meals_count": summary.get("meals_count", len(dailyplan_meals)),
        "foods_count": summary.get("foods_count", len(foods_aggregation)),
    }

    current_weight = get_current_weight(user)
    ppk_dailyplan = {
        "ppk": (dp_protein / current_weight)
        if (current_weight and dp_protein)
        else None,
    }

    dailyplan_meals_table_items = [
        build_dailyplanmeal_table_item(
            dpm,
            dailyplan_snapshot=nutrition_snapshot,
        )
        for dpm in dailyplan_meals
    ]

    menu = build_dailyplan_menu(dailyplan_meals)
    has_dpm = len(dailyplan_meals) > 0

    main_card_data = {
        "main_id": dailyplan.id,
        "title": {
            "name": dailyplan.name,
            "label": "DailyPlan",
            "category": dailyplan.category,
            "category_badge": resolve_category_badge(dailyplan.category),
            "icon": CONTENT_ICON_REGISTRY.get("dailyplan"),
            "meals_count": len(dailyplan_meals),
            "foods_count": structural_indicators["foods_count"],
        },
        "kpis": {
            "ppk": ppk_dailyplan["ppk"],
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
        "table_items": dailyplan_meals_table_items,
        "menu": menu,
        "metadata": {
            "owner": str(dailyplan.created_by),
            "author": str(dailyplan.original_author),
            "fork_from": str(dailyplan.forked_from) if dailyplan.forked_from else None,
        },
        "show_kpis": has_dpm,
        "show_table": has_dpm,
    }

    child_cards_data = []

    for dpm in dailyplan_meals:
        meal = dpm.meal

        meal_total_kcal = meal.total_kcal_cached or meal.total_kcal
        meal_protein = meal.protein_cached or meal.protein
        meal_carbs = meal.carbs_cached or meal.carbs
        meal_fat = meal.fat_cached or meal.fat

        meal_alloc = {
            "protein": meal.alloc_protein_cached or meal.alloc["protein"],
            "carbs": meal.alloc_carbs_cached or meal.alloc["carbs"],
            "fat": meal.alloc_fat_cached or meal.alloc["fat"],
        }

        ppk_meal = get_ppk_meal(meal, user)

        meal_foods = list(meal.meal_food_set.all())
        meal_foods_aggregation = build_meal_foods_aggregation(meal)

        meal_foods_table_items = [
            build_mealfood_table_item(mf)
            for mf in meal_foods
        ]

        child_cards_data.append(
            {
                "main_id": dailyplan.id,
                "child_id": meal.id,
                "foods_aggregation": meal_foods_aggregation,
                "related_data": {
                    "rel_id": dpm.id,
                    "hour": str(dpm.hour) if dpm.hour else None,
                    "note": dpm.note,
                    "alloc_protein": meal_alloc["protein"],
                    "alloc_carbs": meal_alloc["carbs"],
                    "alloc_fat": meal_alloc["fat"],
                },
                "title": {
                    "name": meal.name,
                    "label": "Meal",
                    "icon": CONTENT_ICON_REGISTRY.get("meal"),
                    "category": "en plan",
                    "category_badge": resolve_category_badge("en plan"),
                    "foods_count": len(meal_foods_aggregation),
                    "url": (
                        reverse("dailyplan_meal_detail", args=[dailyplan.id, dpm.id])
                        if viewmode == DAILYPLAN_VIEWMODE_PERSONAL_DETAIL
                        else None
                    ),
                },
                "kpis": {
                    "ppk": ppk_meal["ppk"],
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
                "table_items": meal_foods_table_items,
                "metadata": {
                    "owner": str(meal.created_by),
                    "author": str(meal.original_author),
                    "fork_from": str(meal.forked_from) if meal.forked_from else None,
                },
                "actions": resolve_dailyplan_meal_actions(
                    dpm,
                    user,
                    viewmode,
                ),
            }
        )

    return DailyPlanDetailContentData(
        header=header,
        main_card_data=main_card_data,
        child_cards_data=child_cards_data,
        foods_aggregation=foods_aggregation,
        foods_aggregation_table=foods_aggregation_table,
        structural_indicators=structural_indicators,
    )


def build_dailyplan_list_content_data(dailyplans, user, viewmode, list_mode="list"):
    child_cards_data = []

    if list_mode in {"reorder", "delete"}:
        return DailyPlanListContentData(
            child_cards_data=[
                {
                    "child_id": dailyplan.id,
                    "title": {"name": dailyplan.name},
                }
                for dailyplan in dailyplans
            ]
        )

    current_weight = get_current_weight(user)

    for dailyplan in dailyplans:
        summary = get_dailyplan_summary(dailyplan)
        nutrition_snapshot = summary.get("totals", {})

        dp_total_kcal = nutrition_snapshot.get("total_kcal", 0)
        dp_protein = nutrition_snapshot.get("protein", 0)
        dp_carbs = nutrition_snapshot.get("carbs", 0)
        dp_fat = nutrition_snapshot.get("fat", 0)

        dp_kcal_protein = nutrition_snapshot.get("kcal_protein", 0)
        dp_kcal_carbs = nutrition_snapshot.get("kcal_carbs", 0)
        dp_kcal_fat = nutrition_snapshot.get("kcal_fat", 0)

        dp_alloc = nutrition_snapshot.get("alloc", {"protein": 0, "carbs": 0, "fat": 0})

        ppk = {
            "ppk": (dp_protein / current_weight)
            if (current_weight and dp_protein)
            else None,
        }

        share = next(
            (
                s for s in dailyplan.shares.all()
                if s.accepted_by_id == user.id and not s.removed
            ),
            None,
        )

        actions = []

        actions.extend(
            resolve_dailyplan_entity_actions(
                dailyplan,
                user,
                viewmode,
            )
        )

        if share:
            actions.extend(
                resolve_share_actions(
                    share,
                    user,
                    viewmode,
                )
            )

        child_cards_data.append(
            {
                "child_id": dailyplan.id,
                "title": {
                    "name": dailyplan.name,
                    "label": "DailyPlan",
                    "icon": CONTENT_ICON_REGISTRY.get("dailyplan"),
                    "category": dailyplan.category,
                    "category_badge": resolve_category_badge(dailyplan.category),
                    "meals_count": summary.get("meals_count", 0),
                    "foods_count": summary.get("foods_count", 0),
                },
                "kpis": {
                    "ppk": ppk["ppk"],
                    "tot_kcal": dp_total_kcal,
                    "g_protein": dp_protein,
                    "g_carbs": dp_carbs,
                    "g_fat": dp_fat,
                    "kcal_protein": dp_kcal_protein,
                    "kcal_carbs": dp_kcal_carbs,
                    "kcal_fat": dp_kcal_fat,
                    "alloc_protein": dp_alloc.get("protein", 0),
                    "alloc_carbs": dp_alloc.get("carbs", 0),
                    "alloc_fat": dp_alloc.get("fat", 0),
                },
                "table_items": [item.get("table_item") for item in summary.get("meals", []) if item.get("table_item")],
                "menu": {"meals": summary.get("menu", [])},
                "foods_aggregation": summary.get("foods_aggregation_table", []),
                "metadata": {
                    "owner": str(dailyplan.created_by),
                    "author": str(dailyplan.original_author),
                    "fork_from": str(dailyplan.forked_from) if dailyplan.forked_from else None,
                },
                "actions": actions,
                "if_shared": {
                    "child_id": dailyplan.id,
                    "share_id": share.id if share else None,
                },
            }
        )

    return DailyPlanListContentData(
        child_cards_data=child_cards_data,
    )
