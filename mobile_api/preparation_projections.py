"""Preparation rows shared by the meal library and detail endpoints."""

from django.db.models import Prefetch

from notas.domain.models import MealPreparation, PreparationIngredient


def meal_preparations_prefetch():
    return Prefetch(
        "meal_preparation_set",
        queryset=MealPreparation.objects.select_related("preparation", "version").prefetch_related(
            Prefetch("version__ingredients", queryset=PreparationIngredient.objects.select_related("food"))
        ),
    )


def preparation_panel_item(relation) -> dict:
    version = relation.version
    factor = relation.factor
    ingredients = sorted(version.ingredients.all(), key=lambda row: (row.order, row.id))
    return {
        "relation_id": relation.id,
        "detail_id": relation.preparation_id,
        "name": relation.preparation.name,
        "version": version.version,
        "quantity_g": round(float(relation.quantity_g), 3),
        "selected_units": float(relation.selected_units) if relation.selected_units is not None else None,
        "selection_mode": relation.selection_mode,
        "household_label": version.household_label,
        "calories": round(relation.total_kcal, 1),
        "sodium_mg": round(float(version.sodium_mg) * factor, 1) if version.sodium_mg is not None else None,
        "allergens": version.allergens,
        "ingredients": [{
            "food_id": row.food_id,
            "name": version.ingredients_snapshot[index]["name"],
            "quantity_g": round(float(row.quantity_g) * factor, 3),
            "preparation_state": row.preparation_state,
            "is_condiment": row.is_condiment,
        } for index, row in enumerate(ingredients)],
    }
