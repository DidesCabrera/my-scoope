from notas.application.services.nutrition.food_aggregation import (
    build_meal_foods_projection,
)
from notas.domain.models import Meal, MealFood
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


def rebuild_meals_and_parent_caches_for_food(food):
    """Refresh every cached nutrition projection affected by a Food edit."""
    from notas.application.services.cache.dailyplan_summary import refresh_dailyplans_for_meal

    meal_ids = MealFood.objects.filter(food=food).values_list("meal_id", flat=True).distinct()
    for meal in Meal.objects.filter(pk__in=meal_ids).iterator():
        rebuild_meal_cached_state(meal)
        refresh_dailyplans_for_meal(meal)
