from django.urls import reverse

from notas.presentation.frontend.jscontext.meal_picker import MealPickerContext, MealPickerMealsPayload


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
            "kpis": dailyplan_kpis,
            "meals": [
                {
                    "dailyplanmeal_id": item.id,
                    "meal_id": item.meal_id,
                    "name": item.meal.name,
                    "hour": item.hour.isoformat(timespec="minutes") if item.hour else "",
                    "note": item.note or "",
                }
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


