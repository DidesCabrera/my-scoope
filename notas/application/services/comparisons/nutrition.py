from typing import Any, Callable


def alloc_from_values(total_kcal: float, kcal_protein: float, kcal_carbs: float, kcal_fat: float) -> dict[str, float]:
    if not total_kcal or total_kcal <= 0:
        return {"protein": 0, "carbs": 0, "fat": 0}

    return {
        "protein": (kcal_protein / total_kcal) * 100,
        "carbs": (kcal_carbs / total_kcal) * 100,
        "fat": (kcal_fat / total_kcal) * 100,
    }


def food_values(food: Any, quantity: float) -> dict[str, float]:
    factor = quantity / 100
    protein = food.protein * factor
    carbs = food.carbs * factor
    fat = food.fat * factor
    kcal_protein = food.kcal_protein * factor
    kcal_carbs = food.kcal_carbs * factor
    kcal_fat = food.kcal_fat * factor
    total_kcal = kcal_protein + kcal_carbs + kcal_fat
    alloc = alloc_from_values(total_kcal, kcal_protein, kcal_carbs, kcal_fat)

    return {
        "total_kcal": total_kcal,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "alloc_protein": alloc["protein"],
        "alloc_carbs": alloc["carbs"],
        "alloc_fat": alloc["fat"],
    }


def entity_values(entity: Any, current_weight: float | None = None) -> dict[str, float]:
    alloc = entity.alloc
    protein = entity.protein

    return {
        "total_kcal": entity.total_kcal,
        "ppk": (protein / current_weight) if (current_weight and protein) else 0,
        "protein": protein,
        "carbs": entity.carbs,
        "fat": entity.fat,
        "alloc_protein": alloc.get("protein", 0),
        "alloc_carbs": alloc.get("carbs", 0),
        "alloc_fat": alloc.get("fat", 0),
    }


def comparable_rows(selections, items_by_id: dict[int, Any], value_builder: Callable[[Any, Any], dict[str, float]]):
    rows: list[tuple[Any, dict[str, float]]] = []

    for selection in selections:
        if not selection.id:
            continue

        item = items_by_id.get(selection.id)
        if not item:
            continue

        rows.append((selection, value_builder(item, selection)))

    return rows
