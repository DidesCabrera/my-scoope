from notas.domain.constants.nutrition import (
    CARBS_KCAL_PER_GRAM,
    FAT_KCAL_PER_GRAM,
    PROTEIN_KCAL_PER_GRAM,
)


def kcal_from_macros(protein: float, carbs: float, fat: float) -> float:
    return (
        protein * PROTEIN_KCAL_PER_GRAM
        + carbs * CARBS_KCAL_PER_GRAM
        + fat * FAT_KCAL_PER_GRAM
    )


def macro_kcal_breakdown(protein: float, carbs: float, fat: float) -> dict:
    return {
        "kcal_protein": protein * PROTEIN_KCAL_PER_GRAM,
        "kcal_carbs": carbs * CARBS_KCAL_PER_GRAM,
        "kcal_fat": fat * FAT_KCAL_PER_GRAM,
    }


def macro_allocation(protein: float, carbs: float, fat: float) -> dict:
    total = protein + carbs + fat

    if total == 0:
        return {
            "protein": 0,
            "carbs": 0,
            "fat": 0,
        }

    return {
        "protein": round((protein / total) * 100, 2),
        "carbs": round((carbs / total) * 100, 2),
        "fat": round((fat / total) * 100, 2),
    }


def compute_meal_nutrition(meal) -> dict:
    protein = 0.0
    carbs = 0.0
    fat = 0.0

    kcal_protein = 0.0
    kcal_carbs = 0.0
    kcal_fat = 0.0

    for mf in meal.meal_food_set.all():
        protein += mf.protein
        carbs += mf.carbs
        fat += mf.fat

        kcal_protein += mf.kcal_protein
        kcal_carbs += mf.kcal_carbs
        kcal_fat += mf.kcal_fat

    total_kcal = kcal_protein + kcal_carbs + kcal_fat

    if total_kcal > 0:
        alloc = {
            "protein": kcal_protein / total_kcal * 100,
            "carbs": kcal_carbs / total_kcal * 100,
            "fat": kcal_fat / total_kcal * 100,
        }
    else:
        alloc = {
            "protein": 0,
            "carbs": 0,
            "fat": 0,
        }

    return {
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "kcal_protein": kcal_protein,
        "kcal_carbs": kcal_carbs,
        "kcal_fat": kcal_fat,
        "total_kcal": total_kcal,
        "alloc": alloc,
    }