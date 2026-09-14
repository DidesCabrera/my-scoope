from __future__ import annotations

from datetime import date, datetime

from django.contrib.auth.models import User
from django.db import transaction

from notas.application.services.commands.dailyplan_commands import create_draft_dailyplan
from notas.domain.models import (
    DailyPlan,
    PinnedDailyPlan,
    PinnedDailyPlanMealExecution,
)

MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def default_today_plan_name(local_date: date) -> str:
    return f"Mis comidas del {local_date.day} de {MONTHS[local_date.month - 1]}"


def _owned_dailyplan(*, user, dailyplan_id: int) -> DailyPlan:
    try:
        return DailyPlan.objects.exclude(source=DailyPlan.SOURCE_PROGRAM).get(
            pk=dailyplan_id,
            created_by=user,
        )
    except DailyPlan.DoesNotExist as exc:
        raise ValueError("pinned_dailyplan_not_found") from exc


@transaction.atomic
def pin_dailyplan(*, user, dailyplan_id: int) -> PinnedDailyPlan:
    User.objects.select_for_update().get(pk=user.pk)
    dailyplan = _owned_dailyplan(user=user, dailyplan_id=dailyplan_id)
    pinned, _ = PinnedDailyPlan.objects.update_or_create(
        user=user,
        defaults={"dailyplan": dailyplan, "is_active": True},
    )
    return pinned


@transaction.atomic
def create_and_pin_empty_dailyplan(*, user, local_date: date) -> PinnedDailyPlan:
    User.objects.select_for_update().get(pk=user.pk)
    existing = PinnedDailyPlan.objects.select_related("dailyplan").filter(user=user).first()
    if existing is not None and existing.is_active:
        return existing
    created = create_draft_dailyplan(user=user, name=default_today_plan_name(local_date))
    if existing is not None:
        existing.dailyplan = created.dailyplan
        existing.is_active = True
        existing.save(update_fields=["dailyplan", "is_active", "updated_at"])
        return existing
    return PinnedDailyPlan.objects.create(user=user, dailyplan=created.dailyplan)


@transaction.atomic
def unpin_dailyplan(*, user) -> None:
    PinnedDailyPlan.objects.filter(user=user, is_active=True).update(is_active=False)


def _clean_idempotency_key(value: str) -> str:
    clean = (value or "").strip()
    if not 8 <= len(clean) <= 120:
        raise ValueError("pinned_dailyplan_idempotency_key_invalid")
    return clean


@transaction.atomic
def record_pinned_meal_execution(
    *,
    user,
    local_date: date,
    meal_key: str,
    action: str,
    idempotency_key: str,
    note: str = "",
    food_key: str = "",
    occurred_at: datetime | None = None,
) -> PinnedDailyPlanMealExecution:
    idempotency_key = _clean_idempotency_key(idempotency_key)
    existing = PinnedDailyPlanMealExecution.objects.select_related("pinned_dailyplan").filter(
        idempotency_key=idempotency_key,
    ).first()
    if existing is not None:
        if (
            existing.pinned_dailyplan.user_id == user.id
            and existing.local_date == local_date
            and existing.meal_key == meal_key
            and existing.action == action
            and existing.food_key == food_key
        ):
            return existing
        raise ValueError("pinned_dailyplan_idempotency_conflict")

    try:
        pinned = PinnedDailyPlan.objects.select_for_update().select_related("dailyplan").get(
            user=user,
            is_active=True,
        )
    except PinnedDailyPlan.DoesNotExist as exc:
        raise ValueError("pinned_dailyplan_not_found") from exc

    meal_relations = pinned.dailyplan.dailyplan_meals.prefetch_related("meal__meal_food_set").all()
    meals = {f"dailyplan-meal:{relation.id}": relation for relation in meal_relations}
    relation = meals.get(meal_key)
    if relation is None:
        raise ValueError("pinned_dailyplan_meal_invalid")
    if action not in dict(PinnedDailyPlanMealExecution.ACTION_CHOICES):
        raise ValueError("pinned_dailyplan_action_invalid")
    food_actions = {
        PinnedDailyPlanMealExecution.ACTION_FOOD_PREPARED,
        PinnedDailyPlanMealExecution.ACTION_FOOD_UNPREPARED,
    }
    valid_food_keys = {f"meal-food:{item.id}" for item in relation.meal.meal_food_set.all()}
    if action in food_actions and food_key not in valid_food_keys:
        raise ValueError("pinned_dailyplan_food_invalid")
    if action not in food_actions and food_key:
        raise ValueError("pinned_dailyplan_food_unexpected")
    clean_note = (note or "").strip()
    if len(clean_note) > 500:
        raise ValueError("pinned_dailyplan_note_too_long")

    return PinnedDailyPlanMealExecution.objects.create(
        pinned_dailyplan=pinned,
        local_date=local_date,
        meal_key=meal_key,
        action=action,
        idempotency_key=idempotency_key,
        note=clean_note,
        food_key=food_key,
        occurred_at=occurred_at,
    )
