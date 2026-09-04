from django.urls import reverse

from notas.application.services.food_imports.localized_names import resolve_food_display_name
from notas.presentation.frontend.jscontext.food_picker import FoodPickerFoodsPayload, FoodPickerLegacyContext


def build_food_picker_context_payload(
    *,
    meal,
    nutrition_kpis,
    mealfood,
):
    base = {
        "meal": {
            "id": meal.id,
            "name": meal.name,
            "kpis": nutrition_kpis,
            "foods": [
                {
                    "mealfood_id": meal_food.id,
                    "food_id": meal_food.food_id,
                    "name": resolve_food_display_name(meal_food.food),
                    "quantity": float(meal_food.quantity),
                }
                for meal_food in meal.meal_food_set.all()
            ],
        }
    }

    if mealfood:
        return FoodPickerLegacyContext(
            **base,
            mode="edit",
            editing={
                "mealfood_id": mealfood.id,
                "food_id": mealfood.food_id,
                "original_quantity": float(mealfood.quantity),
            }
        )

    return FoodPickerLegacyContext(
        **base,
        mode="add",
        editing=None,
    )

def build_food_picker_foods_payload(foods):
    payload = []

    for food in foods:
        if hasattr(food, "as_dict"):
            payload.append(food.as_dict())
            continue

        payload.append({
            "id": food.id,
            "name": food.name,
            "protein": food.protein,
            "carbs": food.carbs,
            "fat": food.fat,
            "total_kcal": food.total_kcal,
            "alloc": food.alloc,
        })

    return payload
