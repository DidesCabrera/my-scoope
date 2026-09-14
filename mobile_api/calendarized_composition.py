from __future__ import annotations

from copy import deepcopy

from django.db.models import Prefetch

from mobile_api.api_support import calendarization_error
from mobile_api.errors import MobileAPIError
from notas.application.queries.read_boundaries import get_readable_food_queryset
from notas.application.services.calendarization.snapshots import (
    build_food_snapshot,
    build_meal_snapshot,
    snapshot_totals,
)
from notas.application.services.commands.calendarization_commands import (
    add_food_to_calendarized_meal,
    add_meal_to_calendarized_day,
    replace_calendarized_food,
    replace_calendarized_meal,
)
from notas.application.services.food_imports.localized_names import resolve_food_display_name
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import (
    CalendarizedDay,
    DailyPlanMeal,
    Food,
    Meal,
    MealFood,
    ProgramCalendarization,
)


def _number(value) -> float:
    return round(float(value or 0), 1)


def _percentage(part, total) -> float:
    return _number(float(part or 0) / float(total) * 100) if total and float(total) > 0 else 0.0


def _macro_kcal(totals: dict) -> tuple[float, float, float]:
    return (
        float(totals.get("protein_g") or 0) * 4,
        float(totals.get("carbs_g") or 0) * 4,
        float(totals.get("fat_g") or 0) * 9,
    )


def _total_kcal(totals: dict) -> float:
    stored = totals.get("total_kcal")
    return float(stored) if stored is not None else sum(_macro_kcal(totals))


def _nutrition(totals: dict, current_weight) -> dict:
    protein = float(totals.get("protein_g") or 0)
    carbs = float(totals.get("carbs_g") or 0)
    fat = float(totals.get("fat_g") or 0)
    protein_kcal, carbs_kcal, fat_kcal = _macro_kcal(totals)
    calories = _total_kcal(totals)
    return {
        "calories": _number(calories),
        "protein": {
            "grams": _number(protein),
            "allocation": _percentage(protein_kcal, calories),
            "per_kilogram": _number(protein / current_weight) if current_weight and protein else None,
        },
        "carbs": {"grams": _number(carbs), "allocation": _percentage(carbs_kcal, calories)},
        "fat": {"grams": _number(fat), "allocation": _percentage(fat_kcal, calories)},
    }


def _food_row(food: dict, *, parent_totals: dict, projected: bool = False) -> dict:
    totals = {
        "protein_g": food.get("protein_g"),
        "carbs_g": food.get("carbs_g"),
        "fat_g": food.get("fat_g"),
        "total_kcal": food.get("total_kcal"),
    }
    kcal = _macro_kcal(totals)
    calories = _total_kcal(totals)
    parent_kcal = _macro_kcal(parent_totals)
    return {
        "id": str(food.get("key") or "calendarized-food"),
        "relation_id": None,
        "name": food.get("name") or "Alimento",
        "quantity": _number(food.get("quantity_g")),
        "quantity_unit": "g",
        "calories": _number(calories),
        "calorie_share": _percentage(calories, _total_kcal(parent_totals)),
        "calorie_distribution": {
            "protein": _percentage(kcal[0], calories),
            "carbs": _percentage(kcal[1], calories),
            "fat": _percentage(kcal[2], calories),
        },
        "protein_grams": _number(totals["protein_g"]),
        "carbs_grams": _number(totals["carbs_g"]),
        "fat_grams": _number(totals["fat_g"]),
        "protein_allocation": _percentage(kcal[0], parent_kcal[0]),
        "carbs_allocation": _percentage(kcal[1], parent_kcal[1]),
        "fat_allocation": _percentage(kcal[2], parent_kcal[2]),
        "is_projected": projected,
        "projected_label": "Por agregar" if projected else None,
    }


def _source_meal_ids(meals: list[dict]) -> dict[str, int]:
    result = {
        str(meal.get("key")): int(meal["source_meal_id"])
        for meal in meals
        if isinstance(meal, dict) and meal.get("key") and meal.get("source_meal_id")
    }
    slot_ids = {}
    for meal in meals:
        if not isinstance(meal, dict):
            continue
        key = meal.get("key")
        if not isinstance(key, str) or not key.startswith("dailyplan_meal:"):
            continue
        try:
            slot_ids[int(key.removeprefix("dailyplan_meal:"))] = key
        except ValueError:
            continue
    for slot_id, meal_id in DailyPlanMeal.objects.filter(pk__in=slot_ids).values_list("id", "meal_id"):
        result[slot_ids[slot_id]] = meal_id
    return result


def _meal_row(
    meal: dict,
    *,
    plan_totals: dict,
    source_meal_ids: dict[str, int],
    current_weight,
    projected: bool = False,
    projected_food_key: str | None = None,
) -> dict:
    totals = meal.get("totals") if isinstance(meal.get("totals"), dict) else {}
    kcal = _macro_kcal(totals)
    plan_kcal = _macro_kcal(plan_totals)
    calories = _total_kcal(totals)
    key = str(meal.get("key") or "calendarized-meal")
    return {
        "id": key,
        "relation_id": None,
        "detail_id": source_meal_ids.get(key, 0),
        "name": meal.get("name") or "Comida",
        "time": str(meal.get("hour"))[:5] if meal.get("hour") else None,
        "note": meal.get("note") or "",
        "foods": [
            _food_row(
                food,
                parent_totals=totals,
                projected=bool(projected_food_key and food.get("key") == projected_food_key),
            )
            for food in meal.get("foods", [])
            if isinstance(food, dict)
        ],
        "calories": _number(calories),
        "calorie_share": _percentage(calories, _total_kcal(plan_totals)),
        "calorie_distribution": {
            "protein": _percentage(kcal[0], calories),
            "carbs": _percentage(kcal[1], calories),
            "fat": _percentage(kcal[2], calories),
        },
        "protein_grams": _number(totals.get("protein_g")),
        "protein_per_kilogram": _number(float(totals.get("protein_g") or 0) / current_weight)
        if current_weight and totals.get("protein_g")
        else None,
        "carbs_grams": _number(totals.get("carbs_g")),
        "fat_grams": _number(totals.get("fat_g")),
        "protein_allocation": _percentage(kcal[0], plan_kcal[0]),
        "carbs_allocation": _percentage(kcal[1], plan_kcal[1]),
        "fat_allocation": _percentage(kcal[2], plan_kcal[2]),
        "is_projected": projected,
        "projected_label": "Por agregar" if projected else "Actualizada" if projected_food_key else None,
    }


def _dailyplan_result(*, day_id: int, snapshot: dict, current_weight, projected_meal_key: str) -> dict:
    meals = [meal for meal in snapshot.get("meals", []) if isinstance(meal, dict)]
    totals = snapshot.get("totals") if isinstance(snapshot.get("totals"), dict) else {}
    source_meal_ids = _source_meal_ids(meals)
    food_ids = {
        food.get("source_food_id") or food.get("name")
        for meal in meals
        for food in meal.get("foods", [])
        if isinstance(food, dict)
    }
    return {
        "id": day_id,
        "entity": "dailyPlan",
        "name": snapshot.get("name") or "Plan diario",
        "nutrition": _nutrition(totals, current_weight),
        "indicators": [
            {"icon": "meal", "label": "comidas", "value": len(meals)},
            {"icon": "food", "label": "alimentos", "value": len(food_ids)},
        ],
        "panel": {
            "kind": "meals",
            "foods": [],
            "meals": [
                _meal_row(
                    meal,
                    plan_totals=totals,
                    source_meal_ids=source_meal_ids,
                    current_weight=current_weight,
                    projected=meal.get("key") == projected_meal_key,
                )
                for meal in meals
            ],
            "weeks": [],
        },
    }


def _meal_result(*, day_id: int, meal: dict, current_weight, projected_food_key: str) -> dict:
    totals = meal.get("totals") if isinstance(meal.get("totals"), dict) else {}
    return {
        "id": day_id,
        "entity": "meal",
        "name": meal.get("name") or "Comida",
        "nutrition": _nutrition(totals, current_weight),
        "indicators": [{"icon": "food", "label": "alimentos", "value": len(meal.get("foods", []))}],
        "panel": {
            "kind": "foods",
            "foods": [
                _food_row(food, parent_totals=totals, projected=food.get("key") == projected_food_key)
                for food in meal.get("foods", [])
                if isinstance(food, dict)
            ],
            "meals": [],
            "weeks": [],
        },
    }


def _day_context(*, user, day_id: int) -> tuple[CalendarizedDay, dict]:
    day = (
        CalendarizedDay.objects.select_related("calendarization")
        .filter(pk=day_id, calendarization__user=user)
        .first()
    )
    if day is None:
        raise calendarization_error(ValueError("calendarized_day_not_found"))
    if day.calendarization.status not in ProgramCalendarization.CURRENT_STATUSES:
        raise calendarization_error(ValueError("calendarization_not_current"))
    if not isinstance(day.plan_snapshot, dict):
        raise calendarization_error(ValueError("calendarized_plan_snapshot_invalid"))
    return day, deepcopy(day.plan_snapshot)


def _library_meal(user, meal_id: int) -> Meal:
    meal = (
        Meal.objects.filter(pk=meal_id, created_by=user, is_draft=False, dailyplanmeal__isnull=True)
        .prefetch_related(
            Prefetch("meal_food_set", queryset=MealFood.objects.select_related("food").order_by("order", "id"))
        )
        .first()
    )
    if meal is None:
        raise MobileAPIError("picker_selection_not_found", "La comida seleccionada no está disponible.", 404)
    return meal


def _readable_food(user, food_id: int) -> Food:
    food = get_readable_food_queryset(user).filter(pk=food_id, is_active=True).first()
    if food is None:
        raise MobileAPIError("picker_selection_not_found", "El alimento seleccionado no está disponible.", 404)
    return food


def _snapshot_meal(snapshot: dict, meal_snapshot_key: str) -> dict:
    meals = snapshot.get("meals")
    if not isinstance(meals, list):
        raise calendarization_error(ValueError("calendarized_plan_snapshot_invalid"))
    meal = next(
        (
            item
            for item in meals
            if isinstance(item, dict) and item.get("key") == meal_snapshot_key
        ),
        None,
    )
    if meal is None:
        raise calendarization_error(ValueError("meal_snapshot_key_invalid"))
    return meal


def preview_meal_for_calendarized_day(
    *, user, day_id: int, meal_id: int, hour, note: str, meal_snapshot_key: str | None = None
) -> dict:
    _day, snapshot = _day_context(user=user, day_id=day_id)
    meal = _library_meal(user, meal_id)
    current_weight = get_current_weight(user)
    before = _nutrition(snapshot.get("totals", {}), current_weight)
    meals = snapshot.get("meals")
    if not isinstance(meals, list):
        raise calendarization_error(ValueError("calendarized_plan_snapshot_invalid"))
    projected_key = f"projected_calendarized_meal:{meal.id}"
    if meal_snapshot_key:
        index = next(
            (index for index, item in enumerate(meals) if isinstance(item, dict) and item.get("key") == meal_snapshot_key),
            None,
        )
        if index is None:
            raise calendarization_error(ValueError("meal_snapshot_key_invalid"))
        replaced_name = meals[index].get("name") or "Comida"
        meals[index] = build_meal_snapshot(meal=meal, key=projected_key, order=index, hour=hour, note=note)
    else:
        next_order = max((int(item.get("order") or 0) for item in meals if isinstance(item, dict)), default=-1) + 1
        meals.append(build_meal_snapshot(meal=meal, key=projected_key, order=next_order, hour=hour, note=note))
        replaced_name = None
    snapshot["totals"] = snapshot_totals([item.get("totals", {}) for item in meals if isinstance(item, dict)])
    result = _dailyplan_result(
        day_id=day_id,
        snapshot=snapshot,
        current_weight=current_weight,
        projected_meal_key=projected_key,
    )
    return {
        "selection": {
            "id": meal.id,
            "entity": "meal",
            "name": meal.name,
            "nutrition": _nutrition(build_meal_snapshot(meal=meal, key="selection", order=0, hour=None)["totals"], current_weight),
            "quantity": None,
            "hour": str(hour)[:5] if hour else None,
        },
        "impacts": [{"label": "Plan diario después de reemplazar" if meal_snapshot_key else "Plan diario después de agregar", "entity": "dailyPlan", "before": before, "after": result["nutrition"], "metrics": []}],
        "result": result,
        "replacements": [replaced_name] if replaced_name else [],
        "confirmation_required": False,
    }


def commit_meal_to_calendarized_day(
    *, user, day_id: int, meal_id: int, hour, note: str, meal_snapshot_key: str | None = None
) -> dict:
    _day_context(user=user, day_id=day_id)
    meal = _library_meal(user, meal_id)
    try:
        if meal_snapshot_key:
            replace_calendarized_meal(
                user=user,
                day_id=day_id,
                meal_snapshot_key=meal_snapshot_key,
                meal=meal,
                hour=hour,
                note=note,
            )
        else:
            add_meal_to_calendarized_day(user=user, day_id=day_id, meal=meal, hour=hour, note=note)
    except ValueError as exc:
        raise calendarization_error(exc) from exc
    message = "Comida reemplazada en el plan diario activo." if meal_snapshot_key else "Comida agregada al plan diario activo."
    return {"message": message, "target_id": day_id, "created_id": meal.id}


def preview_food_for_calendarized_meal(
    *, user, day_id: int, meal_snapshot_key: str, food_id: int, quantity: float,
    food_snapshot_key: str | None = None,
) -> dict:
    _day, snapshot = _day_context(user=user, day_id=day_id)
    food = _readable_food(user, food_id)
    meal = _snapshot_meal(snapshot, meal_snapshot_key)
    current_weight = get_current_weight(user)
    before = _nutrition(meal.get("totals", {}), current_weight)
    projected_key = f"projected_calendarized_food:{food.id}"
    foods = meal.get("foods")
    if not isinstance(foods, list):
        raise calendarization_error(ValueError("calendarized_meal_snapshot_invalid"))
    if food_snapshot_key:
        index = next(
            (index for index, item in enumerate(foods) if isinstance(item, dict) and item.get("key") == food_snapshot_key),
            None,
        )
        if index is None:
            raise calendarization_error(ValueError("food_snapshot_key_invalid"))
        replaced_name = foods[index].get("name") or "Alimento"
        foods[index] = build_food_snapshot(food=food, quantity=quantity, key=projected_key)
    else:
        foods.append(build_food_snapshot(food=food, quantity=quantity, key=projected_key))
        replaced_name = None
    meal["totals"] = snapshot_totals(foods)
    snapshot["totals"] = snapshot_totals(
        [item.get("totals", {}) for item in snapshot.get("meals", []) if isinstance(item, dict)]
    )
    result = _meal_result(
        day_id=day_id,
        meal=meal,
        current_weight=current_weight,
        projected_food_key=projected_key,
    )
    selected_totals = build_food_snapshot(food=food, quantity=quantity, key="selection")
    return {
        "selection": {
            "id": food.id,
            "entity": "food",
            "name": resolve_food_display_name(food),
            "nutrition": _nutrition(selected_totals, current_weight),
            "quantity": _number(quantity),
            "hour": None,
        },
        "impacts": [{"label": "Comida después de reemplazar" if food_snapshot_key else "Comida después de agregar", "entity": "meal", "before": before, "after": result["nutrition"], "metrics": []}],
        "result": result,
        "replacements": [replaced_name] if replaced_name else [],
        "confirmation_required": False,
    }


def commit_food_to_calendarized_meal(
    *, user, day_id: int, meal_snapshot_key: str, food_id: int, quantity: float,
    food_snapshot_key: str | None = None,
) -> dict:
    _day_context(user=user, day_id=day_id)
    food = _readable_food(user, food_id)
    try:
        if food_snapshot_key:
            replace_calendarized_food(
                user=user,
                day_id=day_id,
                meal_snapshot_key=meal_snapshot_key,
                food_snapshot_key=food_snapshot_key,
                food=food,
                quantity=quantity,
            )
        else:
            add_food_to_calendarized_meal(
                user=user,
                day_id=day_id,
                meal_snapshot_key=meal_snapshot_key,
                food=food,
                quantity=quantity,
            )
    except ValueError as exc:
        raise calendarization_error(exc) from exc
    message = "Alimento reemplazado en la comida activa." if food_snapshot_key else "Alimento agregado a la comida activa."
    return {"message": message, "target_id": day_id, "created_id": food.id}
