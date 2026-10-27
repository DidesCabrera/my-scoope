from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import time

from django.db.models import Prefetch

from notas.application.services.food_portions import proposed_portion_display
from notas.domain.models import DailyPlan, DailyPlanMeal, FoodPortion, MealFood, Program

SNAPSHOT_SCHEMA_VERSION = "calendarized_dailyplan.v1"


def _meal_foods_for_snapshot():
    default_household_portions = FoodPortion.objects.filter(
        is_default=True,
        household_amount__isnull=False,
    ).exclude(household_measure="")
    return (
        MealFood.objects.select_related("food")
        .prefetch_related(
            Prefetch(
                "food__portions",
                queryset=default_household_portions,
                to_attr="_prefetched_default_household_portions",
            )
        )
        .order_by("order", "id")
    )


@dataclass(frozen=True)
class DailyPlanSnapshotResult:
    payload: dict
    content_hash: str


def program_with_calendarization_content(program_id: int) -> Program:
    return (
        Program.objects.select_related("created_by")
        .prefetch_related(
            Prefetch(
                "program_dailyplan__dailyplan__dailyplan_meals",
                queryset=(
                    DailyPlanMeal.objects.select_related("meal")
                    .prefetch_related(
                        Prefetch(
                            "meal__meal_food_set",
                            queryset=_meal_foods_for_snapshot(),
                        )
                    )
                    .order_by("order", "id")
                ),
            )
        )
        .get(pk=program_id)
    )


def dailyplan_with_calendarization_content(dailyplan_id: int) -> DailyPlan:
    return (
        DailyPlan.objects.select_related("created_by")
        .prefetch_related(
            Prefetch(
                "dailyplan_meals",
                queryset=(
                    DailyPlanMeal.objects.select_related("meal")
                    .prefetch_related(
                        Prefetch(
                            "meal__meal_food_set",
                            queryset=_meal_foods_for_snapshot(),
                        )
                    )
                    .order_by("order", "id")
                ),
            )
        )
        .get(pk=dailyplan_id)
    )


def _round(value, digits=3):
    if value is None:
        return None
    return round(float(value), digits)


def snapshot_content_hash(payload: dict) -> str:
    canonical_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def build_food_snapshot(
    *, food, quantity: float, key: str,
    portion_display_quantity: float | None = None,
    portion_display_measure: str = "",
) -> dict:
    factor = float(quantity) / 100
    protein = float(food.protein or 0) * factor
    carbs = float(food.carbs or 0) * factor
    fat = float(food.fat or 0) * factor
    proposed_quantity, proposed_measure = proposed_portion_display(
        food=food,
        metric_quantity=quantity,
    )
    return {
        "key": key,
        "source_food_id": food.id,
        "name": food.name,
        "quantity_g": _round(quantity),
        "quantity_unit": food.portion_unit,
        "portion_display_quantity": _round(
            proposed_quantity
            if proposed_quantity is not None
            else portion_display_quantity if portion_display_quantity is not None else quantity
        ),
        "portion_display_measure": proposed_measure or portion_display_measure or food.portion_unit,
        "protein_g": _round(protein),
        "carbs_g": _round(carbs),
        "fat_g": _round(fat),
        "total_kcal": _round((protein * 4) + (carbs * 4) + (fat * 9)),
    }


def snapshot_totals(items: list[dict]) -> dict:
    return {
        key: _round(sum(float(item.get(key) or 0) for item in items if isinstance(item, dict)))
        for key in ("protein_g", "carbs_g", "fat_g", "total_kcal")
    }


def build_meal_snapshot(
    *,
    meal,
    key: str,
    order: int,
    hour: time | None,
    note: str = "",
) -> dict:
    foods = [
        build_food_snapshot(
            food=meal_food.food,
            quantity=meal_food.quantity,
            key=f"source_meal_food:{meal_food.id}",
            portion_display_quantity=meal_food.portion_display_quantity,
            portion_display_measure=meal_food.portion_display_measure,
        )
        for meal_food in meal.meal_food_set.all()
    ]
    return {
        "key": key,
        "source_meal_id": meal.id,
        "name": meal.name,
        "order": order,
        "note": note or "",
        "hour": hour.strftime("%H:%M") if hour else None,
        "foods": foods,
        "totals": snapshot_totals(foods),
    }


def build_dailyplan_snapshot(program_day) -> DailyPlanSnapshotResult:
    return build_dailyplan_snapshot_from_dailyplan(
        program_day.dailyplan,
        source_program_day_id=program_day.id,
    )


def build_dailyplan_snapshot_from_dailyplan(
    dailyplan: DailyPlan,
    *,
    source_program_day_id: int | None = None,
) -> DailyPlanSnapshotResult:
    meals = []

    for dailyplan_meal in dailyplan.dailyplan_meals.all():
        meal = dailyplan_meal.meal
        foods = []
        for meal_food in meal.meal_food_set.all():
            food = meal_food.food
            proposed_quantity, proposed_measure = proposed_portion_display(
                food=food,
                metric_quantity=meal_food.quantity,
            )
            foods.append(
                {
                    "key": f"meal_food:{meal_food.id}",
                    "name": food.name,
                    "quantity_g": _round(meal_food.quantity),
                    "quantity_unit": food.portion_unit,
                    "portion_display_quantity": _round(
                        proposed_quantity
                        if proposed_quantity is not None
                        else meal_food.portion_display_quantity
                        if meal_food.portion_display_quantity is not None
                        else meal_food.quantity
                    ),
                    "portion_display_measure": proposed_measure or meal_food.portion_display_measure or food.portion_unit,
                    "protein_g": _round(meal_food.protein),
                    "carbs_g": _round(meal_food.carbs),
                    "fat_g": _round(meal_food.fat),
                    "total_kcal": _round(meal_food.total_kcal),
                }
            )

        meals.append(
            {
                "key": f"dailyplan_meal:{dailyplan_meal.id}",
                "name": meal.name,
                "order": dailyplan_meal.order,
                "note": dailyplan_meal.note or "",
                "hour": dailyplan_meal.hour.strftime("%H:%M") if dailyplan_meal.hour else None,
                "foods": foods,
                "totals": {
                    "protein_g": _round(meal.protein),
                    "carbs_g": _round(meal.carbs),
                    "fat_g": _round(meal.fat),
                    "total_kcal": _round(meal.total_kcal),
                },
            }
        )

    payload = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "source": {
            "program_day_id": source_program_day_id,
            "dailyplan_id": dailyplan.id,
        },
        "name": dailyplan.name,
        "meals": meals,
        "totals": {
            "protein_g": _round(dailyplan.protein),
            "carbs_g": _round(dailyplan.carbs),
            "fat_g": _round(dailyplan.fat),
            "total_kcal": _round(dailyplan.total_kcal),
        },
    }
    return DailyPlanSnapshotResult(
        payload=payload,
        content_hash=snapshot_content_hash(payload),
    )
