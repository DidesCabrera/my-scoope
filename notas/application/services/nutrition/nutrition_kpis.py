from notas.application.services.nutrition.weight import get_current_weight

#=====CALCULO PPK=========

def get_ppk_meal(meal, user):
    weight = get_current_weight(user)
    ppk = (meal.protein / weight) if (weight and meal.protein) else None
    return {
        "ppk": ppk,
    }

def get_ppk_dailyplan(dailyplan, user): 
    weight = get_current_weight(user)
    ppk = (dailyplan.protein / weight) if (weight and dailyplan.protein) else None
    return {
        "ppk": ppk,
    }



def _meal_macro_snapshot(meal):
    protein = meal.protein_cached if meal.protein_cached is not None else meal.protein
    carbs = meal.carbs_cached if meal.carbs_cached is not None else meal.carbs
    fat = meal.fat_cached if meal.fat_cached is not None else meal.fat

    kcal_protein = (
        meal.kcal_protein_cached
        if meal.kcal_protein_cached is not None
        else meal.kcal_protein
    )
    kcal_carbs = (
        meal.kcal_carbs_cached
        if meal.kcal_carbs_cached is not None
        else meal.kcal_carbs
    )
    kcal_fat = (
        meal.kcal_fat_cached
        if meal.kcal_fat_cached is not None
        else meal.kcal_fat
    )

    return {
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "kcal_protein": kcal_protein,
        "kcal_carbs": kcal_carbs,
        "kcal_fat": kcal_fat,
    }


def build_dailyplan_nutrition_snapshot(dailyplan):
    totals = {
        "protein": 0,
        "carbs": 0,
        "fat": 0,
        "kcal_protein": 0,
        "kcal_carbs": 0,
        "kcal_fat": 0,
    }

    for dpm in dailyplan.dailyplan_meals.all():
        meal_totals = _meal_macro_snapshot(dpm.meal)

        for key in totals:
            totals[key] += meal_totals[key]

    total_kcal = (
        totals["kcal_protein"]
        + totals["kcal_carbs"]
        + totals["kcal_fat"]
    )

    if total_kcal > 0:
        alloc = {
            "protein": totals["kcal_protein"] / total_kcal * 100,
            "carbs": totals["kcal_carbs"] / total_kcal * 100,
            "fat": totals["kcal_fat"] / total_kcal * 100,
        }
    else:
        alloc = {
            "protein": 0,
            "carbs": 0,
            "fat": 0,
        }

    return {
        **totals,
        "total_kcal": total_kcal,
        "alloc": alloc,
    }


#=====TRAIDOS DESDE NUTRITION=========

def build_nutrition_kpis_from_meal(meal, user):
    snapshot = _meal_macro_snapshot(meal)
    total_kcal = (
        snapshot["kcal_protein"]
        + snapshot["kcal_carbs"]
        + snapshot["kcal_fat"]
    )

    if total_kcal > 0:
        alloc = {
            "protein": snapshot["kcal_protein"] / total_kcal * 100,
            "carbs": snapshot["kcal_carbs"] / total_kcal * 100,
            "fat": snapshot["kcal_fat"] / total_kcal * 100,
        }
    else:
        alloc = {
            "protein": 0,
            "carbs": 0,
            "fat": 0,
        }

    weight = get_current_weight(user)
    protein = float(snapshot["protein"])
    ppk = (protein / weight) if (weight and protein) else None

    return {
        "total_kcal": float(total_kcal),

        "protein": protein,
        "carbs": float(snapshot["carbs"]),
        "fat": float(snapshot["fat"]),

        "alloc": {
            "protein": float(alloc["protein"]),
            "carbs": float(alloc["carbs"]),
            "fat": float(alloc["fat"]),
        },

        "ppk": {
            "ppk": ppk,
        },
        "weight": weight,
        "kcal_protein": float(snapshot["kcal_protein"]),
        "kcal_carbs": float(snapshot["kcal_carbs"]),
        "kcal_fat": float(snapshot["kcal_fat"]),
    }



def build_nutrition_kpis_from_dailyplan(dailyplan, user):
    snapshot = build_dailyplan_nutrition_snapshot(dailyplan)
    weight = get_current_weight(user)
    protein = float(snapshot["protein"])

    ppk = (protein / weight) if (weight and protein) else None

    return {
        "total_kcal": float(snapshot["total_kcal"]),

        "protein": protein,
        "carbs": float(snapshot["carbs"]),
        "fat": float(snapshot["fat"]),

        "alloc": {
            "protein": float(snapshot["alloc"]["protein"]),
            "carbs": float(snapshot["alloc"]["carbs"]),
            "fat": float(snapshot["alloc"]["fat"]),
        },

        "ppk": {
            "ppk": ppk,
        },
        "weight": weight,
        "kcal_protein": float(snapshot["kcal_protein"]),
        "kcal_carbs": float(snapshot["kcal_carbs"]),
        "kcal_fat": float(snapshot["kcal_fat"]),
    }


