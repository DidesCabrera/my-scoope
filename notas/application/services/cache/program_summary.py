from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from django.db.models import Prefetch
from django.utils import timezone

from notas.application.services.food_imports.localized_names import resolve_food_display_name
from notas.domain.models import DailyPlan, MealFood, Program, ProgramDay
from notas.domain.services.nutrition import macro_kcal_distribution

DAY_LABELS = (
    (1, "Lun"),
    (2, "Mar"),
    (3, "Mié"),
    (4, "Jue"),
    (5, "Vie"),
    (6, "Sáb"),
    (7, "Dom"),
)

PROGRAM_SUMMARY_CACHE_VERSION = 2


def _dailyplan_meals_for(dailyplan: DailyPlan):
    prefetched = getattr(dailyplan, "_prefetched_objects_cache", {}).get("dailyplan_meals")
    if prefetched is not None:
        return sorted(prefetched, key=lambda dpm: (dpm.order, dpm.id))
    return list(
        dailyplan.dailyplan_meals.select_related("meal").prefetch_related(
            Prefetch(
                "meal__meal_food_set",
                queryset=MealFood.objects.select_related("food"),
            )
        ).order_by("order", "id")
    )


def _safe_percentage(part, total):
    if not total or total <= 0:
        return 0.0
    return part / total * 100


def build_dailyplan_snapshot(dailyplan: DailyPlan) -> dict:
    dailyplan_meals = _dailyplan_meals_for(dailyplan)
    protein = sum(dpm.meal.protein for dpm in dailyplan_meals)
    carbs = sum(dpm.meal.carbs for dpm in dailyplan_meals)
    fat = sum(dpm.meal.fat for dpm in dailyplan_meals)
    kcal_protein = sum(dpm.meal.kcal_protein for dpm in dailyplan_meals)
    kcal_carbs = sum(dpm.meal.kcal_carbs for dpm in dailyplan_meals)
    kcal_fat = sum(dpm.meal.kcal_fat for dpm in dailyplan_meals)
    total_kcal = kcal_protein + kcal_carbs + kcal_fat

    return {
        "id": dailyplan.id,
        "name": dailyplan.name,
        "total_kcal": total_kcal,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "kcal_protein": kcal_protein,
        "kcal_carbs": kcal_carbs,
        "kcal_fat": kcal_fat,
        "alloc": {
            "protein": _safe_percentage(kcal_protein, total_kcal),
            "carbs": _safe_percentage(kcal_carbs, total_kcal),
            "fat": _safe_percentage(kcal_fat, total_kcal),
        },
    }


def _empty_totals():
    return {
        "total_kcal": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0,
        "kcal_protein": 0,
        "kcal_carbs": 0,
        "kcal_fat": 0,
        "alloc": {"protein": 0, "carbs": 0, "fat": 0},
    }


def _add_snapshot(totals, snapshot):
    for key in ("total_kcal", "protein", "carbs", "fat", "kcal_protein", "kcal_carbs", "kcal_fat"):
        totals[key] += float(snapshot.get(key) or 0)


def _finalize_totals(totals):
    total_kcal = totals["total_kcal"]
    totals["alloc"] = {
        "protein": _safe_percentage(totals["kcal_protein"], total_kcal),
        "carbs": _safe_percentage(totals["kcal_carbs"], total_kcal),
        "fat": _safe_percentage(totals["kcal_fat"], total_kcal),
    }
    return totals


def _average_totals(totals, divisor=7):
    divisor = divisor or 1
    averaged = {
        "total_kcal": totals["total_kcal"] / divisor,
        "protein": totals["protein"] / divisor,
        "carbs": totals["carbs"] / divisor,
        "fat": totals["fat"] / divisor,
        "kcal_protein": totals["kcal_protein"] / divisor,
        "kcal_carbs": totals["kcal_carbs"] / divisor,
        "kcal_fat": totals["kcal_fat"] / divisor,
        "alloc": {"protein": 0, "carbs": 0, "fat": 0},
    }
    return _finalize_totals(averaged)


def _kpi_from_totals(totals):
    return {
        "tot_kcal": {"value": totals["total_kcal"]},
        "protein": {"g": totals["protein"], "alloc": totals["alloc"]["protein"]},
        "carbs": {"g": totals["carbs"], "alloc": totals["alloc"]["carbs"]},
        "fat": {"g": totals["fat"], "alloc": totals["alloc"]["fat"]},
    }


def _program_days_queryset(program: Program):
    return (
        program.program_dailyplan.select_related("dailyplan")
        .prefetch_related("dailyplan__dailyplan_meals__meal__meal_food_set__food")
        .order_by("week_number", "day_number", "id")
    )


def _program_days_for(program: Program):
    prefetched = getattr(program, "_prefetched_objects_cache", {}).get("program_dailyplan")
    if prefetched is not None:
        return sorted(prefetched, key=lambda program_day: (program_day.week_number, program_day.day_number, program_day.id))
    return list(_program_days_queryset(program))


def _food_row(food, display_name, total_grams, program_totals):
    total_grams = total_grams or 0
    factor = total_grams / 100
    g_protein = food.protein * factor
    g_carbs = food.carbs * factor
    g_fat = food.fat * factor
    kcal_protein = food.kcal_protein * factor
    kcal_carbs = food.kcal_carbs * factor
    kcal_fat = food.kcal_fat * factor
    total_kcal = kcal_protein + kcal_carbs + kcal_fat
    return {
        "child": {"id": food.id},
        "rel": {
            "id": food.id,
            "quantity": total_grams,
            "quantity_unit": "g",
            "name": display_name,
            "total_kcal": total_kcal,
            "kcal_share": _safe_percentage(total_kcal, program_totals.get("total_kcal", 0)),
            "kcal_distribution": macro_kcal_distribution(
                kcal_protein,
                kcal_carbs,
                kcal_fat,
            ),
            "g_protein": g_protein,
            "g_carbs": g_carbs,
            "g_fat": g_fat,
            "alloc_protein": _safe_percentage(kcal_protein, program_totals.get("kcal_protein", 0)),
            "alloc_carbs": _safe_percentage(kcal_carbs, program_totals.get("kcal_carbs", 0)),
            "alloc_fat": _safe_percentage(kcal_fat, program_totals.get("kcal_fat", 0)),
        },
    }


def _foods_table_from_dailyplan_meals(dailyplan_meals, totals):
    aggregation = defaultdict(lambda: {"food": None, "display_name": "", "total_grams": 0})
    for dpm in dailyplan_meals:
        for meal_food in dpm.meal.meal_food_set.all():
            food = meal_food.food
            aggregation[food.id]["food"] = food
            aggregation[food.id]["display_name"] = resolve_food_display_name(food)
            aggregation[food.id]["total_grams"] += meal_food.quantity
    ordered = sorted(aggregation.values(), key=lambda item: (-item["total_grams"], item["display_name"]))
    return [_food_row(item["food"], item["display_name"], item["total_grams"], totals) for item in ordered]


def build_program_summary(program: Program) -> dict:
    program_days = _program_days_for(program)
    slots = {(program_day.week_number, program_day.day_number): program_day for program_day in program_days}
    snapshot_cache = {}
    weeks = []
    program_totals = _empty_totals()
    week_totals_for_variance = []
    program_dailyplan_meals = []

    for week_number in range(1, program.normalized_duration_weeks + 1):
        week_totals = _empty_totals()
        week_dailyplan_meals = []
        days = []

        for day_number, day_label in DAY_LABELS:
            program_day = slots.get((week_number, day_number))
            snapshot = None
            if program_day:
                snapshot = snapshot_cache.setdefault(
                    program_day.dailyplan_id,
                    build_dailyplan_snapshot(program_day.dailyplan),
                )
                dailyplan_meals = _dailyplan_meals_for(program_day.dailyplan)
                week_dailyplan_meals.extend(dailyplan_meals)
                program_dailyplan_meals.extend(dailyplan_meals)
                _add_snapshot(week_totals, snapshot)
                _add_snapshot(program_totals, snapshot)

            days.append({
                "day_number": day_number,
                "day_label": day_label,
                "program_day": {"id": program_day.id} if program_day else None,
                "dailyplan": {"id": program_day.dailyplan_id, "name": program_day.dailyplan.name} if program_day else None,
                "snapshot": snapshot,
            })

        week_totals = _finalize_totals(week_totals)
        week_totals_for_variance.append(week_totals["total_kcal"])
        week_averages = _average_totals(week_totals, divisor=len(DAY_LABELS))
        week_foods_aggregation_table = _foods_table_from_dailyplan_meals(week_dailyplan_meals, week_totals)
        weeks.append({
            "week_number": week_number,
            "days": days,
            "totals": week_totals,
            "averages": week_averages,
            "kpis": _kpi_from_totals(week_totals),
            "average_kpis": _kpi_from_totals(week_averages),
            "filled_days_count": sum(1 for day in days if day["program_day"]),
            "meals_count": len(week_dailyplan_meals),
            "foods_count": len(week_foods_aggregation_table),
            "foods_aggregation_table": week_foods_aggregation_table,
            "foods_panel_id": f"program-week-{week_number}",
        })

    program_totals = _finalize_totals(program_totals)
    program_foods_aggregation_table = _foods_table_from_dailyplan_meals(program_dailyplan_meals, program_totals)
    non_zero_weeks = [value for value in week_totals_for_variance if value > 0]
    avg_week_kcal = (sum(non_zero_weeks) / len(non_zero_weeks)) if non_zero_weeks else 0
    for week in weeks:
        week["kcal_delta_vs_avg"] = week["totals"]["total_kcal"] - avg_week_kcal if avg_week_kcal else 0

    return {
        "version": PROGRAM_SUMMARY_CACHE_VERSION,
        "duration_weeks": program.normalized_duration_weeks,
        "duration_days": program.duration_days,
        "weeks": weeks,
        "program_totals": program_totals,
        "program_kpis": _kpi_from_totals(program_totals),
        "average_week_kcal": avg_week_kcal,
        "filled_days_count": sum(week["filled_days_count"] for week in weeks),
        "program_meals_count": len(program_dailyplan_meals),
        "program_foods_count": len(program_foods_aggregation_table),
        "program_foods_aggregation_table": program_foods_aggregation_table,
    }


def refresh_program_summary_cache(program: Program) -> dict:
    hydrated_program = Program.objects.prefetch_related(
        "program_dailyplan__dailyplan__dailyplan_meals__meal__meal_food_set__food",
    ).get(pk=program.pk)
    summary = build_program_summary(hydrated_program)
    updated_at = timezone.now()
    Program.objects.filter(pk=program.pk).update(
        summary_cache=summary,
        summary_cache_updated_at=updated_at,
    )
    program.summary_cache = summary
    program.summary_cache_updated_at = updated_at
    return summary


def get_program_summary(program: Program) -> dict:
    cached = getattr(program, "summary_cache", None) or {}
    if cached.get("version") == PROGRAM_SUMMARY_CACHE_VERSION:
        return deepcopy(cached)
    return refresh_program_summary_cache(program)
