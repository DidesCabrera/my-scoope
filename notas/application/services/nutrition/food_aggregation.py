from collections import defaultdict

from notas.application.services.food_imports.localized_names import (
    resolve_food_display_name,
)


def build_dailyplan_foods_aggregation(dailyplan_meals):
    foods_aggregation = defaultdict(lambda: {
        "food": None,
        "display_name": "",
        "total_grams": 0,
    })

    for dpm in dailyplan_meals:
        meal = dpm.meal

        for meal_food in meal.meal_food_set.all():
            food = meal_food.food
            grams = meal_food.quantity

            foods_aggregation[food.id]["food"] = food
            foods_aggregation[food.id]["display_name"] = resolve_food_display_name(food)
            foods_aggregation[food.id]["total_grams"] += grams

    return sorted(
        foods_aggregation.values(),
        key=lambda x: (-x["total_grams"], x["display_name"]),
    )


def build_meal_foods_aggregation(meal):
    foods_aggregation = defaultdict(lambda: {
        "food": None,
        "display_name": "",
        "total_grams": 0,
    })

    for meal_food in meal.meal_food_set.all():
        food = meal_food.food
        grams = meal_food.quantity

        foods_aggregation[food.id]["food"] = food
        foods_aggregation[food.id]["display_name"] = resolve_food_display_name(food)
        foods_aggregation[food.id]["total_grams"] += grams

    return sorted(
        foods_aggregation.values(),
        key=lambda x: (-x["total_grams"], x["display_name"]),
    )


def build_meal_foods_projection(meal):
    foods = build_meal_foods_aggregation(meal)

    ordered = sorted(
        foods,
        key=lambda x: (-x["total_grams"], x["display_name"]),
    )

    return [
        {
            "id": f["food"].id,
            "name": f["display_name"],
            "grams": round(f["total_grams"], 1),
            "quantity_unit": f["food"].portion_unit,
        }
        for f in ordered
    ]
