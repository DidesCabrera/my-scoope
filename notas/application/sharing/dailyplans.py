"""DailyPlan adapter for privacy-reviewed, portable share snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Prefetch

from notas.application.sharing.contracts import SHARE_SNAPSHOT_SCHEMA_VERSION
from notas.domain.models import DailyPlan, MealFood, ShareResource


class DailyPlanShareError(ValueError):
    pass


@dataclass(frozen=True)
class DailyPlanShareResult:
    resource: ShareResource


def _number(value: float) -> float:
    return round(float(value or 0), 2)


def _nutrition(*, protein: float, carbs: float, fat: float) -> dict:
    protein = _number(protein)
    carbs = _number(carbs)
    fat = _number(fat)
    calories = _number(protein * 4 + carbs * 4 + fat * 9)
    return {
        "calories": calories,
        "protein_grams": protein,
        "carbs_grams": carbs,
        "fat_grams": fat,
    }


def build_dailyplan_share_snapshot(dailyplan: DailyPlan) -> dict:
    """Return an immutable JSON-safe representation without account or database IDs."""
    meals = []
    plan_protein = 0.0
    plan_carbs = 0.0
    plan_fat = 0.0
    food_count = 0

    for dailyplan_meal in dailyplan.dailyplan_meals.all():
        foods = []
        meal_protein = 0.0
        meal_carbs = 0.0
        meal_fat = 0.0
        for meal_food in dailyplan_meal.meal.meal_food_set.all():
            food_nutrition = _nutrition(
                protein=meal_food.protein,
                carbs=meal_food.carbs,
                fat=meal_food.fat,
            )
            foods.append(
                {
                    "name": meal_food.food.name,
                    "quantity_grams": _number(meal_food.quantity),
                    "nutrition": food_nutrition,
                }
            )
            meal_protein += food_nutrition["protein_grams"]
            meal_carbs += food_nutrition["carbs_grams"]
            meal_fat += food_nutrition["fat_grams"]
            food_count += 1

        meal_nutrition = _nutrition(protein=meal_protein, carbs=meal_carbs, fat=meal_fat)
        plan_protein += meal_nutrition["protein_grams"]
        plan_carbs += meal_nutrition["carbs_grams"]
        plan_fat += meal_nutrition["fat_grams"]
        meals.append(
            {
                "name": dailyplan_meal.meal.name,
                "time": dailyplan_meal.hour.isoformat(timespec="minutes") if dailyplan_meal.hour else None,
                "nutrition": meal_nutrition,
                "foods": foods,
            }
        )

    return {
        "schema_version": SHARE_SNAPSHOT_SCHEMA_VERSION,
        "subject": {"type": ShareResource.SubjectType.DAILY_PLAN, "title": dailyplan.name},
        "summary": {"meal_count": len(meals), "food_count": food_count},
        "nutrition": _nutrition(protein=plan_protein, carbs=plan_carbs, fat=plan_fat),
        "meals": meals,
    }


def _owned_dailyplan(*, sender, dailyplan_id: int) -> DailyPlan:
    dailyplan = (
        DailyPlan.objects.filter(pk=dailyplan_id, created_by=sender)
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .prefetch_related(
            Prefetch(
                "dailyplan_meals__meal__meal_food_set",
                queryset=MealFood.objects.select_related("food").order_by("order", "id"),
            )
        )
        .first()
    )
    if dailyplan is None:
        raise DailyPlanShareError("dailyplan_share_not_available")
    return dailyplan


@transaction.atomic
def create_dailyplan_share_resource(
    *, sender, dailyplan_id: int, claim_policy: str = ShareResource.ClaimPolicy.MULTIPLE
) -> DailyPlanShareResult:
    if claim_policy not in ShareResource.ClaimPolicy.values:
        raise DailyPlanShareError("share_claim_policy_invalid")
    dailyplan = _owned_dailyplan(sender=sender, dailyplan_id=dailyplan_id)
    resource = ShareResource.objects.create(
        sender=sender,
        subject_type=ShareResource.SubjectType.DAILY_PLAN,
        source_object_id=dailyplan.id,
        snapshot=build_dailyplan_share_snapshot(dailyplan),
        snapshot_schema_version=SHARE_SNAPSHOT_SCHEMA_VERSION,
        claim_policy=claim_policy,
    )
    return DailyPlanShareResult(resource=resource)
