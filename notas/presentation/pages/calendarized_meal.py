from __future__ import annotations

from notas.application.queries.calendarization_execution_queries import (
    meal_execution_state_for_day,
)
from notas.application.services.nutrition.weight import get_current_weight


def _number(value) -> float:
    return float(value or 0)


def _percentage(part: float, total: float) -> float:
    return (part / total) * 100 if total > 0 else 0


def _nutrition_totals(payload: dict | None) -> dict:
    totals = payload or {}
    protein = _number(totals.get("protein_g"))
    carbs = _number(totals.get("carbs_g"))
    fat = _number(totals.get("fat_g"))
    calories = _number(totals.get("total_kcal")) or protein * 4 + carbs * 4 + fat * 9
    return {
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "calories": calories,
        "kcal_protein": protein * 4,
        "kcal_carbs": carbs * 4,
        "kcal_fat": fat * 9,
    }


def snapshot_food_table_row(food: dict, meal_calories: float, current_weight=None) -> dict:
    nutrition = _nutrition_totals(food)
    return {
        "child": {"id": food.get("key", "")},
        "rel": {
            "id": food.get("key", ""),
            "quantity": _number(food.get("quantity_g")),
            "quantity_unit": "g",
            "name": food.get("name") or "Alimento",
            "total_kcal": nutrition["calories"],
            "kcal_share": _percentage(nutrition["calories"], meal_calories),
            "kcal_distribution": {
                "protein": _percentage(nutrition["kcal_protein"], nutrition["calories"]),
                "carbs": _percentage(nutrition["kcal_carbs"], nutrition["calories"]),
                "fat": _percentage(nutrition["kcal_fat"], nutrition["calories"]),
            },
            "g_protein": nutrition["protein"],
            "ppk": nutrition["protein"] / current_weight if current_weight and nutrition["protein"] else None,
            "g_carbs": nutrition["carbs"],
            "g_fat": nutrition["fat"],
            "alloc_protein": _percentage(nutrition["kcal_protein"], nutrition["calories"]),
            "alloc_carbs": _percentage(nutrition["kcal_carbs"], nutrition["calories"]),
            "alloc_fat": _percentage(nutrition["kcal_fat"], nutrition["calories"]),
        },
    }


def snapshot_food_card(food: dict, current_weight=None) -> dict:
    nutrition = _nutrition_totals(food)
    return {
        "child_id": food.get("key", ""),
        "related_data": {"quantity": _number(food.get("quantity_g"))},
        "titulo": {"name": food.get("name") or "Alimento", "label": "Food", "icon": "carrot"},
        "kpis": {
            "ppk": nutrition["protein"] / current_weight if current_weight and nutrition["protein"] else None,
            "tot_kcal": nutrition["calories"],
            "g_protein": nutrition["protein"],
            "g_carbs": nutrition["carbs"],
            "g_fat": nutrition["fat"],
            "kcal_protein": nutrition["kcal_protein"],
            "kcal_carbs": nutrition["kcal_carbs"],
            "kcal_fat": nutrition["kcal_fat"],
            "alloc_protein": _percentage(nutrition["kcal_protein"], nutrition["calories"]),
            "alloc_carbs": _percentage(nutrition["kcal_carbs"], nutrition["calories"]),
            "alloc_fat": _percentage(nutrition["kcal_fat"], nutrition["calories"]),
        },
        "actions": [],
    }


def build_calendarized_meal_detail(*, day, meal_snapshot_key: str, user) -> dict | None:
    meals = (day.plan_snapshot or {}).get("meals", [])
    meal = next(
        (item for item in meals if isinstance(item, dict) and item.get("key") == meal_snapshot_key),
        None,
    )
    if meal is None:
        return None

    execution = next(
        (item for item in meal_execution_state_for_day(day) if item["meal_key"] == meal_snapshot_key),
        {
            "meal_key": meal_snapshot_key,
            "status": "planned",
            "note": "",
            "recorded_at": None,
        },
    )
    nutrition = _nutrition_totals(meal.get("totals"))
    current_weight = get_current_weight(user)
    foods = [item for item in meal.get("foods", []) if isinstance(item, dict)]
    completed = execution["status"] == "completed"
    has_note = bool(execution["note"].strip())
    return {
        "day": day,
        "meal": meal,
        "execution": execution,
        "completed": completed,
        "completed_count": int(completed),
        "has_note": has_note,
        "note_count": int(has_note),
        "foods_count": len(foods),
        "titulo": {
            "name": meal.get("name") or "Comida",
            "label": "Meal",
            "icon": "utensils",
            "structural_indicators": {
                "foods_count": len(foods),
                "hour": meal.get("hour"),
            },
        },
        "foods_aggregation": [{"display_name": item.get("name") or "Alimento"} for item in foods],
        "food_rows": [snapshot_food_table_row(item, nutrition["calories"], current_weight) for item in foods],
        "food_cards": [snapshot_food_card(item, current_weight) for item in foods],
        "kpis": {
            "ppk": nutrition["protein"] / current_weight if current_weight else 0,
            "tot_kcal": nutrition["calories"],
            "g_protein": nutrition["protein"],
            "g_carbs": nutrition["carbs"],
            "g_fat": nutrition["fat"],
            "kcal_protein": nutrition["kcal_protein"],
            "kcal_carbs": nutrition["kcal_carbs"],
            "kcal_fat": nutrition["kcal_fat"],
            "alloc_protein": _percentage(nutrition["kcal_protein"], nutrition["calories"]),
            "alloc_carbs": _percentage(nutrition["kcal_carbs"], nutrition["calories"]),
            "alloc_fat": _percentage(nutrition["kcal_fat"], nutrition["calories"]),
        },
    }
