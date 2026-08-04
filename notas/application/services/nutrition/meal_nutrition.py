from notas.application.services.nutrition.food_aggregation import (
    build_meal_foods_projection,
)
from notas.domain.services.nutrition import compute_meal_nutrition


def rebuild_meal_cached_state(meal):
    data = compute_meal_nutrition(meal)

    meal.protein_cached = data["protein"]
    meal.carbs_cached = data["carbs"]
    meal.fat_cached = data["fat"]

    meal.kcal_protein_cached = data["kcal_protein"]
    meal.kcal_carbs_cached = data["kcal_carbs"]
    meal.kcal_fat_cached = data["kcal_fat"]
    meal.total_kcal_cached = data["total_kcal"]

    meal.alloc_protein_cached = data["alloc"]["protein"]
    meal.alloc_carbs_cached = data["alloc"]["carbs"]
    meal.alloc_fat_cached = data["alloc"]["fat"]

    meal.foods_aggregation_cached = build_meal_foods_projection(meal)

    meal.save(
        update_fields=[
            "protein_cached",
            "carbs_cached",
            "fat_cached",
            "kcal_protein_cached",
            "kcal_carbs_cached",
            "kcal_fat_cached",
            "total_kcal_cached",
            "alloc_protein_cached",
            "alloc_carbs_cached",
            "alloc_fat_cached",
            "foods_aggregation_cached",
        ]
    )