"""Entity adapters for immutable, portable sharing snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils import timezone

from notas.application.sharing.contracts import SHARE_SNAPSHOT_SCHEMA_VERSION
from notas.application.sharing.dailyplans import build_dailyplan_share_snapshot
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    Meal,
    MealFood,
    Program,
    ProgramDay,
    ShareResource,
)


class EntityShareError(ValueError):
    pass


@dataclass(frozen=True)
class EntityShareResult:
    resource: ShareResource


def _number(value) -> float:
    return round(float(value or 0), 2)


def _nutrition(*, protein, carbs, fat) -> dict:
    protein = _number(protein)
    carbs = _number(carbs)
    fat = _number(fat)
    return {
        "calories": _number(protein * 4 + carbs * 4 + fat * 9),
        "protein_grams": protein,
        "carbs_grams": carbs,
        "fat_grams": fat,
    }


def _resource_expiry():
    ttl_days = max(1, int(getattr(settings, "SHARING_RESOURCE_TTL_DAYS", 30)))
    return timezone.now() + timedelta(days=ttl_days)


def build_food_share_snapshot(food: Food) -> dict:
    return {
        "schema_version": SHARE_SNAPSHOT_SCHEMA_VERSION,
        "subject": {"type": ShareResource.SubjectType.FOOD, "title": food.name},
        "summary": {"basis_grams": 100},
        "nutrition": _nutrition(protein=food.protein, carbs=food.carbs, fat=food.fat),
    }


def _meal_snapshot(meal: Meal, *, variant: str = "library", time=None) -> dict:
    foods = []
    protein = carbs = fat = 0.0
    for meal_food in meal.meal_food_set.all():
        item_nutrition = _nutrition(
            protein=meal_food.protein,
            carbs=meal_food.carbs,
            fat=meal_food.fat,
        )
        foods.append(
            {
                "name": meal_food.food.name,
                "quantity_grams": _number(meal_food.quantity),
                "nutrition": item_nutrition,
            }
        )
        protein += item_nutrition["protein_grams"]
        carbs += item_nutrition["carbs_grams"]
        fat += item_nutrition["fat_grams"]
    subject = {"type": ShareResource.SubjectType.MEAL, "title": meal.name}
    if variant != "library":
        subject["variant"] = variant
    snapshot = {
        "schema_version": SHARE_SNAPSHOT_SCHEMA_VERSION,
        "subject": subject,
        "summary": {"food_count": len(foods)},
        "nutrition": _nutrition(protein=protein, carbs=carbs, fat=fat),
        "foods": foods,
    }
    if time is not None:
        snapshot["time"] = time.isoformat(timespec="minutes") if hasattr(time, "isoformat") else str(time)[:5]
    return snapshot


def build_meal_share_snapshot(meal: Meal) -> dict:
    return _meal_snapshot(meal)


def build_dailyplanmeal_share_snapshot(dailyplan_meal: DailyPlanMeal) -> dict:
    return _meal_snapshot(
        dailyplan_meal.meal,
        variant="daily_plan_meal",
        time=dailyplan_meal.hour,
    )


def build_program_share_snapshot(program: Program) -> dict:
    days = []
    protein = carbs = fat = 0.0
    meal_count = food_count = 0
    for program_day in program.program_dailyplan.all():
        plan = build_dailyplan_share_snapshot(program_day.dailyplan)
        nutrition = plan["nutrition"]
        protein += nutrition["protein_grams"]
        carbs += nutrition["carbs_grams"]
        fat += nutrition["fat_grams"]
        meal_count += plan["summary"]["meal_count"]
        food_count += plan["summary"]["food_count"]
        days.append(
            {
                "week_number": program_day.week_number,
                "day_number": program_day.day_number,
                "plan": plan,
            }
        )
    return {
        "schema_version": SHARE_SNAPSHOT_SCHEMA_VERSION,
        "subject": {"type": ShareResource.SubjectType.PROGRAM, "title": program.name},
        "summary": {
            "duration_weeks": program.normalized_duration_weeks,
            "filled_days": len(days),
            "meal_count": meal_count,
            "food_count": food_count,
        },
        "nutrition": _nutrition(protein=protein, carbs=carbs, fat=fat),
        "days": days,
    }


def _meal_queryset():
    return Meal.objects.prefetch_related(
        Prefetch(
            "meal_food_set",
            queryset=MealFood.objects.select_related("food").order_by("order", "id"),
        )
    )


def _dailyplan_queryset():
    return DailyPlan.objects.prefetch_related(
        Prefetch(
            "dailyplan_meals__meal__meal_food_set",
            queryset=MealFood.objects.select_related("food").order_by("order", "id"),
        )
    )


def _load_owned_subject(*, sender, subject_type: str, subject_id: int, variant: str = ""):
    if subject_type == ShareResource.SubjectType.DAILY_PLAN:
        return (
            _dailyplan_queryset()
            .filter(pk=subject_id, created_by=sender)
            .exclude(source=DailyPlan.SOURCE_PROGRAM)
            .first()
        )
    if subject_type == ShareResource.SubjectType.FOOD:
        return Food.objects.filter(pk=subject_id, created_by=sender, is_active=True).first()
    if subject_type == ShareResource.SubjectType.MEAL and variant == "daily_plan_meal":
        return (
            DailyPlanMeal.objects.select_related("dailyplan", "meal")
            .prefetch_related(
                Prefetch(
                    "meal__meal_food_set",
                    queryset=MealFood.objects.select_related("food").order_by("order", "id"),
                )
            )
            .filter(pk=subject_id, dailyplan__created_by=sender)
            .first()
        )
    if subject_type == ShareResource.SubjectType.MEAL:
        return _meal_queryset().filter(pk=subject_id, created_by=sender).first()
    if subject_type == ShareResource.SubjectType.PROGRAM:
        return (
            Program.objects.filter(pk=subject_id, created_by=sender)
            .prefetch_related(
                Prefetch(
                    "program_dailyplan",
                    queryset=ProgramDay.objects.select_related("dailyplan").prefetch_related(
                        Prefetch(
                            "dailyplan__dailyplan_meals__meal__meal_food_set",
                            queryset=MealFood.objects.select_related("food").order_by("order", "id"),
                        )
                    ),
                )
            )
            .first()
        )
    return None


def _snapshot_for(subject_type: str, instance, *, variant: str = "") -> dict:
    if subject_type == ShareResource.SubjectType.DAILY_PLAN:
        return build_dailyplan_share_snapshot(instance)
    if subject_type == ShareResource.SubjectType.FOOD:
        return build_food_share_snapshot(instance)
    if subject_type == ShareResource.SubjectType.MEAL and variant == "daily_plan_meal":
        return build_dailyplanmeal_share_snapshot(instance)
    if subject_type == ShareResource.SubjectType.MEAL:
        return build_meal_share_snapshot(instance)
    if subject_type == ShareResource.SubjectType.PROGRAM:
        return build_program_share_snapshot(instance)
    raise EntityShareError("share_subject_not_supported")


@transaction.atomic
def get_or_create_entity_share_resource(
    *, sender, subject_type: str, subject_id: int, claim_policy: str = ShareResource.ClaimPolicy.MULTIPLE,
    variant: str = ""
) -> EntityShareResult:
    if subject_type not in ShareResource.SubjectType.values:
        raise EntityShareError("share_subject_not_supported")
    if claim_policy not in ShareResource.ClaimPolicy.values:
        raise EntityShareError("share_claim_policy_invalid")
    instance = _load_owned_subject(
        sender=sender,
        subject_type=subject_type,
        subject_id=subject_id,
        variant=variant,
    )
    if instance is None:
        raise EntityShareError("share_subject_not_available")
    type(instance).objects.select_for_update().get(pk=instance.pk)
    snapshot = _snapshot_for(subject_type, instance, variant=variant)
    candidates = ShareResource.objects.filter(
        sender=sender,
        subject_type=subject_type,
        source_object_id=subject_id,
        status=ShareResource.Status.ACTIVE,
        claim_policy=claim_policy,
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
    if variant:
        candidates = candidates.filter(snapshot__subject__variant=variant)
    else:
        candidates = candidates.exclude(snapshot__subject__variant__isnull=False)
    latest = candidates.order_by("-created_at", "-id").first()
    if latest is not None and latest.snapshot == snapshot:
        return EntityShareResult(resource=latest)
    resource = ShareResource.objects.create(
        sender=sender,
        subject_type=subject_type,
        source_object_id=subject_id,
        snapshot=snapshot,
        snapshot_schema_version=SHARE_SNAPSHOT_SCHEMA_VERSION,
        claim_policy=claim_policy,
        expires_at=_resource_expiry(),
    )
    return EntityShareResult(resource=resource)


def get_or_create_food_share_resource(*, sender, food_id: int, claim_policy=ShareResource.ClaimPolicy.MULTIPLE):
    return get_or_create_entity_share_resource(
        sender=sender, subject_type=ShareResource.SubjectType.FOOD, subject_id=food_id, claim_policy=claim_policy
    )


def get_or_create_meal_share_resource(*, sender, meal_id: int, claim_policy=ShareResource.ClaimPolicy.MULTIPLE):
    return get_or_create_entity_share_resource(
        sender=sender, subject_type=ShareResource.SubjectType.MEAL, subject_id=meal_id, claim_policy=claim_policy
    )


def get_or_create_dailyplanmeal_share_resource(
    *, sender, dailyplan_meal_id: int, claim_policy=ShareResource.ClaimPolicy.MULTIPLE
):
    return get_or_create_entity_share_resource(
        sender=sender,
        subject_type=ShareResource.SubjectType.MEAL,
        subject_id=dailyplan_meal_id,
        claim_policy=claim_policy,
        variant="daily_plan_meal",
    )


def get_or_create_program_share_resource(
    *, sender, program_id: int, claim_policy=ShareResource.ClaimPolicy.MULTIPLE
):
    return get_or_create_entity_share_resource(
        sender=sender, subject_type=ShareResource.SubjectType.PROGRAM, subject_id=program_id, claim_policy=claim_policy
    )
