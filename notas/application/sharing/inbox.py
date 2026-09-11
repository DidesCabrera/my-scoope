"""Inbox lifecycle and snapshot hydration for normalized shares."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from notas.application.sharing.services import ShareUnavailable
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, InboxItem, Meal, MealFood, ShareResource


def _clean_name(value, fallback: str) -> str:
    return (str(value or "").strip() or fallback)[:100]


def _number(value) -> float:
    try:
        return max(float(value or 0), 0)
    except (TypeError, ValueError) as exc:
        raise ShareUnavailable("share_snapshot_invalid") from exc


@transaction.atomic
def save_dailyplan_inbox_item(*, inbox_item: InboxItem, actor) -> DailyPlan:
    item = InboxItem.objects.select_for_update().select_related("resource").get(pk=inbox_item.pk)
    if item.owner_id != actor.id:
        raise ShareUnavailable("share_inbox_item_not_owned")
    if item.resource.subject_type != ShareResource.SubjectType.DAILY_PLAN:
        raise ShareUnavailable("share_snapshot_subject_not_supported")
    if item.saved_subject_type and item.saved_object_id:
        existing = DailyPlan.objects.filter(pk=item.saved_object_id, created_by=actor).first()
        if existing is not None:
            return existing

    snapshot = item.resource.snapshot
    try:
        title = _clean_name(snapshot["subject"]["title"], "Plan compartido")
        meals = snapshot["meals"]
    except (KeyError, TypeError) as exc:
        raise ShareUnavailable("share_snapshot_invalid") from exc
    if not isinstance(meals, list):
        raise ShareUnavailable("share_snapshot_invalid")

    dailyplan = DailyPlan.objects.create(
        name=title,
        created_by=actor,
        source=DailyPlan.SOURCE_MANUAL,
        is_draft=False,
    )
    for meal_position, meal_snapshot in enumerate(meals):
        if not isinstance(meal_snapshot, dict):
            raise ShareUnavailable("share_snapshot_invalid")
        meal = Meal.objects.create(
            name=_clean_name(meal_snapshot.get("name"), "Comida compartida"),
            created_by=actor,
            is_draft=False,
        )
        foods = meal_snapshot.get("foods", [])
        if not isinstance(foods, list):
            raise ShareUnavailable("share_snapshot_invalid")
        for food_position, food_snapshot in enumerate(foods):
            if not isinstance(food_snapshot, dict):
                raise ShareUnavailable("share_snapshot_invalid")
            nutrition = food_snapshot.get("nutrition") or {}
            food = Food.objects.create(
                name=_clean_name(food_snapshot.get("name"), "Alimento compartido"),
                protein=_number(nutrition.get("protein_grams")),
                carbs=_number(nutrition.get("carbs_grams")),
                fat=_number(nutrition.get("fat_grams")),
                created_by=actor,
            )
            quantity = _number(food_snapshot.get("quantity_grams"))
            # Snapshot nutrition is for the shared quantity. Food stores values per 100 g.
            if quantity > 0:
                factor = 100 / quantity
                food.protein = _number(nutrition.get("protein_grams")) * factor
                food.carbs = _number(nutrition.get("carbs_grams")) * factor
                food.fat = _number(nutrition.get("fat_grams")) * factor
                food.save(update_fields=["protein", "carbs", "fat"])
            MealFood.objects.create(meal=meal, food=food, quantity=quantity, order=food_position)
        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal,
            hour=meal_snapshot.get("time") or None,
            order=meal_position,
        )

    item.saved_at = timezone.now()
    item.saved_subject_type = ShareResource.SubjectType.DAILY_PLAN
    item.saved_object_id = dailyplan.id
    item.save(update_fields=["saved_at", "saved_subject_type", "saved_object_id", "updated_at"])
    return dailyplan
