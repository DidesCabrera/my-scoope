from django.urls import reverse

from notas.application.services.nutrition.food_aggregation import (
    build_meal_foods_projection,
)
from notas.presentation.frontend.jscontext.meal_picker import MealPickerContext, MealPickerMealsPayload


def _cached_or_live(meal, cached_attr, live_attr):
    cached_value = getattr(meal, cached_attr, None)
    return cached_value if cached_value is not None else getattr(meal, live_attr)


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


def build_meal_picker_context_payload(
    *,
    dailyplan,
    dailyplan_kpis,
    dailyplan_meals,
    dpm,
):
    base = {
        "dailyplan": {
            "id": dailyplan.id,
            "name": dailyplan.name,
            "owner": str(dailyplan.created_by),
            "kpis": dailyplan_kpis,
            "meals": [
                _serialize_dailyplan_meal(item)
                for item in dailyplan_meals
            ],
        }
    }

    if dpm:
        if dpm:
            return MealPickerContext(
                **base,
                mode="edit",
                editing={
                    "dailyplanmeal_id": dpm.id,
                    "hour": dpm.hour,
                    "note": dpm.note,

                    "original_kpis": {
                        "protein": dpm.meal.protein_cached,
                        "carbs": dpm.meal.carbs_cached,
                        "fat": dpm.meal.fat_cached,
                        "total_kcal": dpm.meal.total_kcal_cached,
                    }
                }
            )


    return MealPickerContext(
        **base,
        mode="add",
        editing=None,
    )


def _compute_meal_ppk(meal, current_weight):
    if not current_weight:
        return None

    protein = meal.protein_cached

    if protein is None:
        protein = meal.protein

    if not protein:
        return None

    return protein / current_weight


def build_meal_picker_meals_payload(meals_qs, *, current_weight=None):
    return MealPickerMealsPayload(
        meals=[
            serialize_meal(m, current_weight=current_weight)
            for m in meals_qs
        ]
    )


def serialize_meal(m, *, current_weight=None):
    return {
        "id": m.id,
        "name": m.name,
        "detail_url": reverse("meal_detail", args=[m.id]),
        "total_kcal": m.total_kcal_cached,
        "protein": m.protein_cached,
        "carbs": m.carbs_cached,
        "fat": m.fat_cached,
        "ppk": _compute_meal_ppk(m, current_weight),
        "alloc": {
            "protein": m.alloc_protein_cached,
            "carbs": m.alloc_carbs_cached,
            "fat": m.alloc_fat_cached,
        },
        "foods": m.foods_aggregation_cached,
    }


def build_meal_picker_data_payload(
    *,
    browse_meals_qs,
    existing_meals_qs,
    current_weight=None,
):
    return {
        "browse_meals": [
            serialize_meal(m, current_weight=current_weight)
            for m in browse_meals_qs
        ],
        "existing_meals": [
            serialize_meal(m, current_weight=current_weight)
            for m in existing_meals_qs
        ],
    }
