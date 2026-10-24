from dataclasses import dataclass

from django.db import transaction

from notas.application.services.commands.meal_commands import save_meal
from notas.domain.models import Meal, MealCatalogEntry


@dataclass(frozen=True)
class SaveCatalogMealResult:
    meal: Meal
    already_saved: bool


@transaction.atomic
def save_catalog_meal_to_library(*, entry: MealCatalogEntry, user) -> SaveCatalogMealResult:
    """Save one stable, user-owned snapshot of a published catalog meal."""
    existing = (
        Meal.objects.select_for_update()
        .filter(
            created_by=user,
            forked_from=entry.meal,
            scope=Meal.Scope.LIBRARY,
        )
        .order_by("id")
        .first()
    )
    if existing is not None:
        return SaveCatalogMealResult(meal=existing, already_saved=True)

    saved_meal = save_meal(entry.meal, user)
    if saved_meal.name != entry.meal.name:
        saved_meal.name = entry.meal.name
        saved_meal.save(update_fields=["name"])

    return SaveCatalogMealResult(meal=saved_meal, already_saved=False)
