from notas.application.services.food_imports.localized_names import resolve_food_display_name
from notas.application.services.nutrition.food_aggregation import build_meal_foods_projection
from notas.presentation.frontend.jscontext.dpm_food_picker import DpmFoodPickerContextPayload


def _cached_or_live(entity, cached_attr, live_attr):
    cached_value = getattr(entity, cached_attr, None)
    return cached_value if cached_value is not None else getattr(entity, live_attr)


def _serialize_meal_food(meal_food):
    return {
        "mealfood_id": meal_food.id,
        "food_id": meal_food.food_id,
        "name": resolve_food_display_name(meal_food.food),
        "quantity": float(meal_food.quantity),
        "protein": float(meal_food.protein),
        "carbs": float(meal_food.carbs),
        "fat": float(meal_food.fat),
        "total_kcal": float(meal_food.total_kcal),
    }


def _serialize_dailyplan_meal(item):
    meal = item.meal
    foods = meal.foods_aggregation_cached
    if foods is None:
        foods = build_meal_foods_projection(meal)

    return {
        "dailyplanmeal_id": item.id,
        "meal_id": item.meal_id,
        "name": meal.name,
        "hour": item.hour.isoformat(timespec="minutes") if item.hour else "",
        "note": item.note or "",
        "protein": _cached_or_live(meal, "protein_cached", "protein"),
        "carbs": _cached_or_live(meal, "carbs_cached", "carbs"),
        "fat": _cached_or_live(meal, "fat_cached", "fat"),
        "total_kcal": _cached_or_live(meal, "total_kcal_cached", "total_kcal"),
        "foods": foods,
    }


def build_dpm_food_picker_context_payload(
    *,
    meal,
    meal_kpis,
    dailyplan,
    dailyplan_kpis,
    mealfood=None,
    dpm=None,
    meal_foods=None,
    dailyplan_meals=None,
):
    meal_foods = list(meal_foods or [])
    dailyplan_meals = list(dailyplan_meals or [])
    base = {
        "meal": {
            "id": meal.id,
            "name": meal.name or "",
            "owner": str(meal.created_by) if meal.created_by_id else "",
            "kpis": meal_kpis,
            "foods": [_serialize_meal_food(item) for item in meal_foods],
        },
        "dailyplan": {
            "id": dailyplan.id,
            "name": dailyplan.name or "",
            "owner": str(dailyplan.created_by) if dailyplan.created_by_id else "",
            "kpis": dailyplan_kpis,
            "meals": [_serialize_dailyplan_meal(item) for item in dailyplan_meals],
        },
        "dpm": {
            "id": dpm.id if dpm else None,
            "hour": dpm.hour.isoformat(timespec="minutes") if dpm and dpm.hour else "",
            "note": dpm.note or "" if dpm else "",
        },
    }

    if mealfood:
        return DpmFoodPickerContextPayload(
            **base,
            mode="edit",
            editing={
                "mealfood_id": mealfood.id,
                "food_id": mealfood.food_id,
                "original_quantity": float(mealfood.quantity),
            },
        )

    return DpmFoodPickerContextPayload(
        **base,
        mode="add",
        editing=None,
    )
