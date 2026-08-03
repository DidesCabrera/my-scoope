"""Composable nutrition object builders for tests."""

from notas.domain.models import DailyPlan, Food, Meal, MealFood


def create_food(*, created_by, name: str = "Test food", **overrides) -> Food:
    values = {
        "name": name,
        "protein": 10,
        "carbs": 20,
        "fat": 5,
        "created_by": created_by,
    }
    values.update(overrides)
    return Food.objects.create(**values)


def create_meal(*, created_by, name: str = "Test meal", **overrides) -> Meal:
    values = {
        "name": name,
        "created_by": created_by,
        "is_public": False,
        "is_draft": False,
    }
    values.update(overrides)
    return Meal.objects.create(**values)


def attach_food(*, meal: Meal, food: Food, quantity=100, order: int = 1) -> MealFood:
    return MealFood.objects.create(meal=meal, food=food, quantity=quantity, order=order)


def create_dailyplan(*, created_by, name: str = "Test daily plan", **overrides) -> DailyPlan:
    values = {
        "name": name,
        "created_by": created_by,
        "is_public": False,
        "is_draft": False,
    }
    values.update(overrides)
    return DailyPlan.objects.create(**values)
