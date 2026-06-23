from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from django.db.models import Prefetch
from django.utils import timezone

from notas.application.services.food_imports.localized_names import resolve_food_display_name
from notas.domain.models import DailyPlan, DailyPlanMeal, MealFood, Program

DAILYPLAN_SUMMARY_CACHE_VERSION = 1


def _safe_percentage(part, total):
    if not total or total <= 0:
        return 0.0
    return part / total * 100


def _cached_or_live(obj, cached_attr, live_attr):
    cached_value = getattr(obj, cached_attr, None)
    return cached_value if cached_value is not None else getattr(obj, live_attr)


def _dailyplan_meals_base_queryset():
    return (
        DailyPlanMeal.objects.select_related(
            "dailyplan",
            "meal",
            "meal__created_by",
            "meal__original_author",
            "meal__forked_from",
        )
        .prefetch_related(
            Prefetch(
                "meal__meal_food_set",
                queryset=MealFood.objects.select_related("food").order_by("order", "id"),
            )
        )
        .order_by("order", "id")
    )


def dailyplan_meals_for_summary(dailyplan: DailyPlan):
    prefetched = getattr(dailyplan, "_prefetched_objects_cache", {}).get("dailyplan_meals")
    if prefetched is not None:
        return sorted(prefetched, key=lambda dpm: (dpm.order, dpm.id))
    return list(_dailyplan_meals_base_queryset().filter(dailyplan=dailyplan))


def _meal_snapshot(meal) -> dict:
    kcal_protein = _cached_or_live(meal, "kcal_protein_cached", "kcal_protein")
    kcal_carbs = _cached_or_live(meal, "kcal_carbs_cached", "kcal_carbs")
    kcal_fat = _cached_or_live(meal, "kcal_fat_cached", "kcal_fat")
    total_kcal = _cached_or_live(meal, "total_kcal_cached", "total_kcal")
    protein = _cached_or_live(meal, "protein_cached", "protein")
    carbs = _cached_or_live(meal, "carbs_cached", "carbs")
    fat = _cached_or_live(meal, "fat_cached", "fat")
    alloc = getattr(meal, "alloc", {})
    meal_foods = list(meal.meal_food_set.all())
    return {
        "id": meal.id,
        "name": meal.name,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "kcal_protein": kcal_protein,
        "kcal_carbs": kcal_carbs,
        "kcal_fat": kcal_fat,
        "total_kcal": total_kcal,
        "alloc": {
            "protein": alloc.get("protein", 0),
            "carbs": alloc.get("carbs", 0),
            "fat": alloc.get("fat", 0),
        },
        "foods_count": len(meal.foods_aggregation_cached or meal_foods),
    }


def _empty_totals():
    return {
        "protein": 0,
        "carbs": 0,
        "fat": 0,
        "kcal_protein": 0,
        "kcal_carbs": 0,
        "kcal_fat": 0,
        "total_kcal": 0,
        "alloc": {"protein": 0, "carbs": 0, "fat": 0},
    }


def _finalize_totals(totals):
    totals["total_kcal"] = totals["kcal_protein"] + totals["kcal_carbs"] + totals["kcal_fat"]
    totals["alloc"] = {
        "protein": _safe_percentage(totals["kcal_protein"], totals["total_kcal"]),
        "carbs": _safe_percentage(totals["kcal_carbs"], totals["total_kcal"]),
        "fat": _safe_percentage(totals["kcal_fat"], totals["total_kcal"]),
    }
    return totals


def _format_quantity(value):
    if value is None:
        return "0"
    numeric_value = float(value)
    if numeric_value.is_integer():
        return str(int(numeric_value))
    return f"{numeric_value:.1f}".rstrip("0").rstrip(".")


def _food_table_row(food, display_name, total_grams, dailyplan_totals):
    factor = (total_grams or 0) / 100
    g_protein = food.protein * factor
    g_carbs = food.carbs * factor
    g_fat = food.fat * factor
    kcal_protein = food.kcal_protein * factor
    kcal_carbs = food.kcal_carbs * factor
    kcal_fat = food.kcal_fat * factor
    total_kcal = kcal_protein + kcal_carbs + kcal_fat
    return {
        "child": {"id": food.id, "name": display_name},
        "rel": {
            "id": food.id,
            "quantity": total_grams,
            "quantity_unit": "g",
            "name": display_name,
            "total_kcal": total_kcal,
            "kcal_share": _safe_percentage(total_kcal, dailyplan_totals["total_kcal"]),
            "g_protein": g_protein,
            "g_carbs": g_carbs,
            "g_fat": g_fat,
            "alloc_protein": _safe_percentage(kcal_protein, dailyplan_totals["kcal_protein"]),
            "alloc_carbs": _safe_percentage(kcal_carbs, dailyplan_totals["kcal_carbs"]),
            "alloc_fat": _safe_percentage(kcal_fat, dailyplan_totals["kcal_fat"]),
        },
    }


def build_dailyplan_summary(dailyplan: DailyPlan) -> dict:
    dailyplan_meals = dailyplan_meals_for_summary(dailyplan)
    totals = _empty_totals()
    meals = []
    foods_aggregation = defaultdict(lambda: {"food": None, "display_name": "", "total_grams": 0})

    for dpm in dailyplan_meals:
        meal = dpm.meal
        snapshot = _meal_snapshot(meal)
        for key in ("protein", "carbs", "fat", "kcal_protein", "kcal_carbs", "kcal_fat"):
            totals[key] += float(snapshot.get(key) or 0)

        meal_foods = list(meal.meal_food_set.all())
        menu_foods = []
        meal_item = {
            "dpm_id": dpm.id,
            "meal_id": meal.id,
            "meal_name": meal.name,
            "hour": str(dpm.hour) if dpm.hour else None,
            "note": dpm.note,
            "order": dpm.order,
            "snapshot": snapshot,
            "foods_count": snapshot["foods_count"],
            "menu_foods": menu_foods,
        }
        meals.append(meal_item)

        for meal_food in meal_foods:
            food = meal_food.food
            display_name = resolve_food_display_name(food)
            foods_aggregation[food.id]["food"] = food
            foods_aggregation[food.id]["display_name"] = display_name
            foods_aggregation[food.id]["total_grams"] += meal_food.quantity
            menu_foods.append(f"{display_name} ({_format_quantity(meal_food.quantity)}g)")

    totals = _finalize_totals(totals)

    for meal_item in meals:
        snapshot = meal_item["snapshot"]
        meal_item["table_item"] = {
            "main_id": dailyplan.id,
            "child_id": meal_item["meal_id"],
            "rel": {
                "id": meal_item["dpm_id"],
                "hour": meal_item["hour"],
                "note": meal_item["note"],
                "name": meal_item["meal_name"],
                "total_kcal": snapshot["total_kcal"],
                "kcal_share": _safe_percentage(snapshot["total_kcal"], totals["total_kcal"]),
                "g_protein": snapshot["protein"],
                "g_carbs": snapshot["carbs"],
                "g_fat": snapshot["fat"],
                "alloc_protein": _safe_percentage(snapshot["kcal_protein"], totals["kcal_protein"]),
                "alloc_carbs": _safe_percentage(snapshot["kcal_carbs"], totals["kcal_carbs"]),
                "alloc_fat": _safe_percentage(snapshot["kcal_fat"], totals["kcal_fat"]),
            },
        }

    ordered_foods = sorted(
        foods_aggregation.values(),
        key=lambda item: (-item["total_grams"], item["display_name"]),
    )
    foods_aggregation_table = [
        _food_table_row(item["food"], item["display_name"], item["total_grams"], totals)
        for item in ordered_foods
    ]

    return {
        "version": DAILYPLAN_SUMMARY_CACHE_VERSION,
        "totals": totals,
        "meals": meals,
        "meals_count": len(meals),
        "foods_count": len(foods_aggregation_table),
        "foods_aggregation_table": foods_aggregation_table,
        "menu": [
            {
                "meal_name": item["meal_name"],
                "foods": item.get("menu_foods", []),
                "target_id": f"dailyplan-meal-step-{item['dpm_id']}",
            }
            for item in meals
        ],
    }


def refresh_dailyplan_summary_cache(dailyplan: DailyPlan) -> dict:
    hydrated = (
        DailyPlan.objects.select_related("created_by", "original_author", "forked_from")
        .prefetch_related(
            Prefetch("dailyplan_meals", queryset=_dailyplan_meals_base_queryset())
        )
        .get(pk=dailyplan.pk)
    )
    summary = build_dailyplan_summary(hydrated)
    updated_at = timezone.now()
    DailyPlan.objects.filter(pk=dailyplan.pk).update(
        summary_cache=summary,
        summary_cache_updated_at=updated_at,
    )
    dailyplan.summary_cache = summary
    dailyplan.summary_cache_updated_at = updated_at
    return summary


def get_dailyplan_summary(dailyplan: DailyPlan) -> dict:
    cached = getattr(dailyplan, "summary_cache", None) or {}
    if cached.get("version") == DAILYPLAN_SUMMARY_CACHE_VERSION:
        return deepcopy(cached)
    return refresh_dailyplan_summary_cache(dailyplan)


def refresh_program_caches_for_dailyplan(dailyplan: DailyPlan) -> None:
    from notas.application.services.cache.program_summary import refresh_program_summary_cache

    programs = Program.objects.filter(program_dailyplan__dailyplan=dailyplan).distinct()
    for program in programs:
        refresh_program_summary_cache(program)


def refresh_dailyplan_and_related_program_caches(dailyplan: DailyPlan) -> dict:
    summary = refresh_dailyplan_summary_cache(dailyplan)
    refresh_program_caches_for_dailyplan(dailyplan)
    return summary


def refresh_dailyplans_for_meal(meal) -> None:
    dailyplans = DailyPlan.objects.filter(dailyplan_meals__meal=meal).distinct()
    for dailyplan in dailyplans:
        refresh_dailyplan_and_related_program_caches(dailyplan)
