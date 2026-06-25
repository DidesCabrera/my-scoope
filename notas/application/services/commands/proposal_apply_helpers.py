from datetime import time

from notas.application.queries.read_boundaries import get_readable_food_queryset
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood, NutritionProposal


def get_readable_food_for_apply(
    *,
    user,
    food_id: int,
) -> Food:
    food = (
        get_readable_food_queryset(user)
        .filter(pk=food_id)
        .first()
    )

    if not food:
        raise ValueError("proposal_apply_food_not_available")

    return food


def create_meal_from_apply_plan(
    *,
    user,
    apply_plan,
) -> Meal:
    meal = Meal.objects.create(
        name=apply_plan.meal.name,
        created_by=user,
        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
        pending_dailyplan=None,
        forked_from=None,
        original_author=None,
    )

    for index, food_item in enumerate(apply_plan.meal.foods, start=1):
        food = get_readable_food_for_apply(
            user=user,
            food_id=food_item.food_id,
        )

        MealFood.objects.create(
            meal=meal,
            food=food,
            quantity=food_item.quantity,
            order=index,
        )

    meal.refresh_from_db()

    return meal


def parse_apply_hour(hour: str | None):
    if not hour:
        return None

    hour_part, minute_part = hour.split(":")

    return time(
        hour=int(hour_part),
        minute=int(minute_part),
    )


def create_snapshot_meal_from_apply_meal(
    *,
    user,
    apply_meal,
) -> Meal:
    meal = Meal.objects.create(
        name=apply_meal.name,
        created_by=user,
        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
        pending_dailyplan=None,
        forked_from=None,
        original_author=None,
    )

    for index, food_item in enumerate(apply_meal.foods, start=1):
        food = get_readable_food_for_apply(
            user=user,
            food_id=food_item.food_id,
        )

        MealFood.objects.create(
            meal=meal,
            food=food,
            quantity=food_item.quantity,
            order=index,
        )

    meal.refresh_from_db()

    return meal


def normalize_dailyplan_source_from_proposal(
    proposal: NutritionProposal,
) -> str:
    source = proposal.source

    allowed_sources = {
        DailyPlan.SOURCE_MANUAL,
        DailyPlan.SOURCE_AI,
        DailyPlan.SOURCE_SYSTEM,
        DailyPlan.SOURCE_MCP,
    }

    if source in allowed_sources:
        return source

    return DailyPlan.SOURCE_AI


def create_dailyplan_from_apply_plan(
    *,
    user,
    proposal: NutritionProposal,
    apply_plan,
) -> DailyPlan:
    dailyplan = DailyPlan.objects.create(
        name=apply_plan.dailyplan.name,
        created_by=user,
        source=normalize_dailyplan_source_from_proposal(proposal),
        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
        forked_from=None,
        original_author=None,
    )

    for index, dailyplan_meal in enumerate(
        apply_plan.dailyplan.meals,
        start=1,
    ):
        snapshot_meal = create_snapshot_meal_from_apply_meal(
            user=user,
            apply_meal=dailyplan_meal.meal,
        )

        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=snapshot_meal,
            hour=parse_apply_hour(dailyplan_meal.hour),
            note=(dailyplan_meal.note or "").strip() or None,
            order=index,
        )

    dailyplan.refresh_from_db()

    return dailyplan


def build_applied_create_meal_metadata(
    *,
    meal: Meal,
    intent: str,
) -> dict:
    return {
        "intent": intent,
        "meal_id": meal.id,
        "meal_name": meal.name,
        "foods": [
            {
                "food_id": meal_food.food_id,
                "food_name": meal_food.food.name,
                "quantity": float(meal_food.quantity),
                "unit": "g",
                "order": meal_food.order,
            }
            for meal_food in (
                meal.meal_food_set
                .select_related("food")
                .all()
            )
        ],
    }


def build_applied_create_dailyplan_metadata(
    *,
    dailyplan: DailyPlan,
    intent: str,
) -> dict:
    return {
        "intent": intent,
        "dailyplan_id": dailyplan.id,
        "dailyplan_name": dailyplan.name,
        "source": dailyplan.source,
        "meals": [
            {
                "dailyplan_meal_id": dailyplan_meal.id,
                "meal_id": dailyplan_meal.meal_id,
                "meal_name": dailyplan_meal.meal.name,
                "hour": (
                    dailyplan_meal.hour.strftime("%H:%M")
                    if dailyplan_meal.hour
                    else None
                ),
                "note": dailyplan_meal.note or "",
                "order": dailyplan_meal.order,
            }
            for dailyplan_meal in (
                dailyplan.dailyplan_meals
                .select_related("meal")
                .all()
            )
        ],
    }
