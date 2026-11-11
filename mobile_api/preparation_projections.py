"""Preparation rows shared by the meal library and detail endpoints."""

from decimal import Decimal

from django.db.models import Prefetch

from notas.domain.models import MealPreparation, PreparationIngredient


def ingredient_payload(row, snapshot: dict, factor: Decimal) -> dict:
    """Project frozen ingredient nutrition for a served portion."""
    quantity = row.quantity_g * factor
    per_100g = snapshot["nutrition_per_100g"]
    macro_factor = quantity / Decimal("100")
    protein = Decimal(str(per_100g["protein_g"])) * macro_factor
    carbs = Decimal(str(per_100g["carbs_g"])) * macro_factor
    fat = Decimal(str(per_100g["fat_g"])) * macro_factor
    return {
        "food_id": row.food_id,
        "name": snapshot["name"],
        "quantity_g": round(float(quantity), 3),
        "preparation_state": row.preparation_state,
        "is_condiment": row.is_condiment,
        "protein_g": round(float(protein), 3),
        "carbs_g": round(float(carbs), 3),
        "fat_g": round(float(fat), 3),
        "calories": round(float(protein * 4 + carbs * 4 + fat * 9), 3),
    }


def meal_preparations_prefetch():
    return Prefetch(
        "meal_preparation_set",
        queryset=MealPreparation.objects.select_related("preparation", "version").prefetch_related(
            Prefetch("version__ingredients", queryset=PreparationIngredient.objects.select_related("food"))
        ),
    )


def preparation_panel_item(relation) -> dict:
    version = relation.version
    factor = Decimal(str(relation.factor))
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
        "protein_g": round(float(version.protein_g * factor), 3),
        "carbs_g": round(float(version.carbs_g * factor), 3),
        "fat_g": round(float(version.fat_g * factor), 3),
        "sodium_mg": round(float(version.sodium_mg * factor), 1) if version.sodium_mg is not None else None,
        "allergens": version.allergens,
        "ingredients": [ingredient_payload(row, version.ingredients_snapshot[index], factor) for index, row in enumerate(ingredients)],
    }
