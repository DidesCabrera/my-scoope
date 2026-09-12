"""Inbox lifecycle and snapshot hydration for normalized shares."""

from __future__ import annotations

import math
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from notas.application.sharing.contracts import SHARE_SNAPSHOT_SCHEMA_VERSION
from notas.application.sharing.services import ShareUnavailable
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    InboxItem,
    Meal,
    MealFood,
    Program,
    ProgramDay,
    ShareResource,
)


@dataclass(frozen=True)
class SavedInboxSubject:
    entity: str
    instance: object


def _clean_name(value, fallback: str) -> str:
    return (str(value or "").strip() or fallback)[:100]


def _number(value) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError) as exc:
        raise ShareUnavailable("share_snapshot_invalid") from exc
    if not math.isfinite(number):
        raise ShareUnavailable("share_snapshot_invalid")
    return max(number, 0)


def _snapshot_title(snapshot: dict, fallback: str) -> str:
    subject = snapshot.get("subject")
    if not isinstance(subject, dict):
        raise ShareUnavailable("share_snapshot_invalid")
    return _clean_name(subject.get("title"), fallback)


def _food_from_snapshot(*, snapshot: dict, actor, quantity_grams: float = 100) -> Food:
    nutrition = snapshot.get("nutrition") or {}
    if not isinstance(nutrition, dict):
        raise ShareUnavailable("share_snapshot_invalid")
    quantity = _number(quantity_grams)
    factor = 100 / quantity if quantity > 0 else 0
    return Food.objects.create(
        name=_clean_name(snapshot.get("name"), "") or _snapshot_title(snapshot, "Alimento compartido"),
        protein=_number(nutrition.get("protein_grams")) * factor,
        carbs=_number(nutrition.get("carbs_grams")) * factor,
        fat=_number(nutrition.get("fat_grams")) * factor,
        created_by=actor,
    )


def _meal_from_snapshot(*, snapshot: dict, actor) -> Meal:
    meal = Meal.objects.create(
        name=_clean_name(snapshot.get("name"), "") or _snapshot_title(snapshot, "Comida compartida"),
        created_by=actor,
        is_draft=False,
    )
    foods = snapshot.get("foods", [])
    if not isinstance(foods, list):
        raise ShareUnavailable("share_snapshot_invalid")
    for position, food_snapshot in enumerate(foods):
        if not isinstance(food_snapshot, dict):
            raise ShareUnavailable("share_snapshot_invalid")
        quantity = _number(food_snapshot.get("quantity_grams"))
        food = _food_from_snapshot(snapshot=food_snapshot, actor=actor, quantity_grams=quantity)
        MealFood.objects.create(meal=meal, food=food, quantity=quantity, order=position)
    return meal


def _dailyplan_from_snapshot(*, snapshot: dict, actor, source: str = DailyPlan.SOURCE_MANUAL) -> DailyPlan:
    try:
        title = _clean_name(snapshot["subject"]["title"], "Plan compartido")
        meals = snapshot["meals"]
    except (KeyError, TypeError) as exc:
        raise ShareUnavailable("share_snapshot_invalid") from exc
    if not isinstance(meals, list):
        raise ShareUnavailable("share_snapshot_invalid")
    dailyplan = DailyPlan.objects.create(name=title, created_by=actor, source=source, is_draft=False)
    for position, meal_snapshot in enumerate(meals):
        if not isinstance(meal_snapshot, dict):
            raise ShareUnavailable("share_snapshot_invalid")
        meal = _meal_from_snapshot(snapshot=meal_snapshot, actor=actor)
        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal,
            hour=meal_snapshot.get("time") or None,
            order=position,
        )
    return dailyplan


def _program_from_snapshot(*, snapshot: dict, actor) -> Program:
    try:
        title = _clean_name(snapshot["subject"]["title"], "Programa compartido")
        days = snapshot["days"]
    except (KeyError, TypeError) as exc:
        raise ShareUnavailable("share_snapshot_invalid") from exc
    if not isinstance(days, list):
        raise ShareUnavailable("share_snapshot_invalid")
    duration_weeks = max(1, int((snapshot.get("summary") or {}).get("duration_weeks") or 1))
    program = Program.objects.create(
        name=title,
        created_by=actor,
        duration_weeks=duration_weeks,
        is_draft=False,
    )
    for day_snapshot in days:
        if not isinstance(day_snapshot, dict) or not isinstance(day_snapshot.get("plan"), dict):
            raise ShareUnavailable("share_snapshot_invalid")
        try:
            week_number = int(day_snapshot["week_number"])
            day_number = int(day_snapshot["day_number"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ShareUnavailable("share_snapshot_invalid") from exc
        if week_number < 1 or week_number > duration_weeks or day_number < 1 or day_number > 7:
            raise ShareUnavailable("share_snapshot_invalid")
        dailyplan = _dailyplan_from_snapshot(
            snapshot=day_snapshot["plan"], actor=actor, source=DailyPlan.SOURCE_PROGRAM
        )
        ProgramDay.objects.create(
            program=program,
            dailyplan=dailyplan,
            week_number=week_number,
            day_number=day_number,
        )
    return program


@transaction.atomic
def update_inbox_item(
    *,
    inbox_item: InboxItem,
    actor,
    is_read: bool | None = None,
    is_favorite: bool | None = None,
    dismissed: bool | None = None,
) -> InboxItem:
    item = InboxItem.objects.select_for_update().get(pk=inbox_item.pk)
    if item.owner_id != actor.id:
        raise ShareUnavailable("share_inbox_item_not_owned")
    now = timezone.now()
    update_fields = ["updated_at"]
    if is_read is not None:
        item.read_at = now if is_read else None
        update_fields.append("read_at")
    if is_favorite is not None:
        item.is_favorite = is_favorite
        update_fields.append("is_favorite")
    if dismissed is not None:
        item.dismissed_at = now if dismissed else None
        update_fields.append("dismissed_at")
    item.save(update_fields=update_fields)
    return item


@transaction.atomic
def save_inbox_item(*, inbox_item: InboxItem, actor) -> SavedInboxSubject:
    item = InboxItem.objects.select_for_update().select_related("resource").get(pk=inbox_item.pk)
    if item.owner_id != actor.id:
        raise ShareUnavailable("share_inbox_item_not_owned")
    model_by_type = {
        ShareResource.SubjectType.DAILY_PLAN: DailyPlan,
        ShareResource.SubjectType.FOOD: Food,
        ShareResource.SubjectType.MEAL: Meal,
        ShareResource.SubjectType.PROGRAM: Program,
    }
    entity_by_type = {
        ShareResource.SubjectType.DAILY_PLAN: "dailyPlan",
        ShareResource.SubjectType.FOOD: "food",
        ShareResource.SubjectType.MEAL: "meal",
        ShareResource.SubjectType.PROGRAM: "program",
    }
    model = model_by_type.get(item.resource.subject_type)
    if model is None:
        raise ShareUnavailable("share_snapshot_subject_not_supported")
    if item.saved_subject_type and item.saved_object_id:
        existing = model.objects.filter(pk=item.saved_object_id, created_by=actor).first()
        if existing is not None:
            return SavedInboxSubject(entity=entity_by_type[item.resource.subject_type], instance=existing)

    snapshot = item.resource.snapshot
    if not isinstance(snapshot, dict):
        raise ShareUnavailable("share_snapshot_invalid")
    subject = snapshot.get("subject")
    if (
        item.resource.snapshot_schema_version != SHARE_SNAPSHOT_SCHEMA_VERSION
        or snapshot.get("schema_version") != SHARE_SNAPSHOT_SCHEMA_VERSION
        or not isinstance(subject, dict)
        or subject.get("type") != item.resource.subject_type
    ):
        raise ShareUnavailable("share_snapshot_version_not_supported")
    if item.resource.subject_type == ShareResource.SubjectType.DAILY_PLAN:
        saved = _dailyplan_from_snapshot(snapshot=snapshot, actor=actor)
    elif item.resource.subject_type == ShareResource.SubjectType.FOOD:
        saved = _food_from_snapshot(snapshot=snapshot, actor=actor)
    elif item.resource.subject_type == ShareResource.SubjectType.MEAL:
        saved = _meal_from_snapshot(snapshot=snapshot, actor=actor)
    else:
        saved = _program_from_snapshot(snapshot=snapshot, actor=actor)

    item.saved_at = timezone.now()
    item.saved_subject_type = item.resource.subject_type
    item.saved_object_id = saved.id
    item.save(update_fields=["saved_at", "saved_subject_type", "saved_object_id", "updated_at"])
    return SavedInboxSubject(entity=entity_by_type[item.resource.subject_type], instance=saved)


def save_dailyplan_inbox_item(*, inbox_item: InboxItem, actor) -> DailyPlan:
    """Compatibility wrapper for callers migrating to the entity-neutral service."""
    result = save_inbox_item(inbox_item=inbox_item, actor=actor)
    if result.entity != "dailyPlan":
        raise ShareUnavailable("share_snapshot_subject_not_supported")
    return result.instance
