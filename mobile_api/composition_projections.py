"""Read-only projections used by the native composition pickers."""

from __future__ import annotations

from collections import defaultdict

from notas.application.services.food_imports.localized_names import resolve_food_display_name
from notas.domain.models import ProgramDay
from notas.domain.services.nutrition import macro_kcal_distribution

DAY_LABELS = {
    1: "Lunes",
    2: "Martes",
    3: "Miércoles",
    4: "Jueves",
    5: "Viernes",
    6: "Sábado",
    7: "Domingo",
}


def _number(value) -> float:
    return round(float(value or 0), 1)


def _percentage(part, total) -> float:
    return _number(float(part or 0) / float(total) * 100) if total and float(total) > 0 else 0.0


def _macros(entity) -> tuple[float, float, float]:
    return float(entity.protein or 0), float(entity.carbs or 0), float(entity.fat or 0)


def _kcal(entity) -> tuple[float, float, float]:
    return float(entity.kcal_protein or 0), float(entity.kcal_carbs or 0), float(entity.kcal_fat or 0)


def _subtract(left, right):
    return tuple(left[index] - right[index] for index in range(3))


def _add(left, right):
    return tuple(left[index] + right[index] for index in range(3))


def _nutrition(macros, kcal, current_weight) -> dict:
    protein, carbs, fat = macros
    protein_kcal, carbs_kcal, fat_kcal = kcal
    total_kcal = protein_kcal + carbs_kcal + fat_kcal
    return {
        "calories": _number(total_kcal),
        "protein": {
            "grams": _number(protein),
            "allocation": _percentage(protein_kcal, total_kcal),
            "per_kilogram": _number(protein / current_weight) if current_weight and protein else None,
        },
        "carbs": {"grams": _number(carbs), "allocation": _percentage(carbs_kcal, total_kcal)},
        "fat": {"grams": _number(fat), "allocation": _percentage(fat_kcal, total_kcal)},
    }


def entity_nutrition(entity, current_weight) -> dict:
    return _nutrition(_macros(entity), _kcal(entity), current_weight)


def _food_row(*, food, quantity, relation_id, parent_kcal, projected=False, projected_label=None, row_id=None):
    factor = float(quantity) / 100
    macros = tuple(value * factor for value in _macros(food))
    kcal = tuple(value * factor for value in _kcal(food))
    total = sum(kcal)
    distribution = macro_kcal_distribution(*kcal)
    return {
        "id": row_id or (f"meal-food:{relation_id}" if relation_id else f"projected-food:{food.id}"),
        "relation_id": relation_id,
        "name": resolve_food_display_name(food),
        "quantity": _number(quantity),
        "quantity_unit": "g",
        "calories": _number(total),
        "calorie_share": _percentage(total, sum(parent_kcal)),
        "calorie_distribution": {key: _number(value) for key, value in distribution.items()},
        "protein_grams": _number(macros[0]),
        "carbs_grams": _number(macros[1]),
        "fat_grams": _number(macros[2]),
        "protein_allocation": _percentage(kcal[0], parent_kcal[0]),
        "carbs_allocation": _percentage(kcal[1], parent_kcal[1]),
        "fat_allocation": _percentage(kcal[2], parent_kcal[2]),
        "is_projected": projected,
        "projected_label": projected_label,
    }


def _meal_food_rows(meal, parent_kcal):
    return [
        _food_row(
            food=relation.food,
            quantity=relation.quantity,
            relation_id=relation.id,
            parent_kcal=parent_kcal,
        )
        for relation in meal.meal_food_set.select_related("food").order_by("order", "id")
    ]


def project_meal_result(*, meal, food, quantity, current_weight, replaced=None) -> dict:
    before_macros = _macros(meal)
    before_kcal = _kcal(meal)
    replaced_macros = _macros(replaced) if replaced else (0.0, 0.0, 0.0)
    replaced_kcal = _kcal(replaced) if replaced else (0.0, 0.0, 0.0)
    factor = float(quantity) / 100
    selected_macros = tuple(value * factor for value in _macros(food))
    selected_kcal = tuple(value * factor for value in _kcal(food))
    result_macros = _add(_subtract(before_macros, replaced_macros), selected_macros)
    result_kcal = _add(_subtract(before_kcal, replaced_kcal), selected_kcal)
    rows = [
        _food_row(
            food=relation.food,
            quantity=relation.quantity,
            relation_id=relation.id,
            parent_kcal=result_kcal,
        )
        for relation in meal.meal_food_set.select_related("food").order_by("order", "id")
        if not replaced or relation.id != replaced.id
    ]
    rows.append(
        _food_row(
            food=food,
            quantity=quantity,
            relation_id=replaced.id if replaced else None,
            parent_kcal=result_kcal,
            projected=True,
            projected_label="Reemplazo" if replaced else "Por agregar",
            row_id=f"projected-meal-food:{replaced.id if replaced else food.id}",
        )
    )
    return {
        "id": meal.id,
        "entity": "meal",
        "name": meal.name,
        "nutrition": _nutrition(result_macros, result_kcal, current_weight),
        "indicators": [{"icon": "food", "label": "alimentos", "value": len(rows)}],
        "panel": {"kind": "foods", "foods": rows, "meals": [], "weeks": []},
    }


def _meal_row(*, meal, relation_id, hour, note, parent_kcal, current_weight, projected=False, projected_label=None, projected_macros=None, projected_kcal=None, projected_foods=None):
    macros = projected_macros or _macros(meal)
    kcal = projected_kcal or _kcal(meal)
    return {
        "id": f"projected-dailyplan-meal:{relation_id or meal.id}" if projected else f"dailyplan-meal:{relation_id}",
        "relation_id": relation_id,
        "detail_id": meal.id,
        "name": meal.name,
        "time": str(hour)[:5] if hour else None,
        "note": note or "",
        "foods": projected_foods if projected_foods is not None else _meal_food_rows(meal, _kcal(meal)),
        "calories": _number(sum(kcal)),
        "calorie_share": _percentage(sum(kcal), sum(parent_kcal)),
        "calorie_distribution": {key: _number(value) for key, value in macro_kcal_distribution(*kcal).items()},
        "protein_grams": _number(macros[0]),
        "protein_per_kilogram": _number(macros[0] / current_weight) if current_weight and macros[0] else None,
        "carbs_grams": _number(macros[1]),
        "fat_grams": _number(macros[2]),
        "protein_allocation": _percentage(kcal[0], parent_kcal[0]),
        "carbs_allocation": _percentage(kcal[1], parent_kcal[1]),
        "fat_allocation": _percentage(kcal[2], parent_kcal[2]),
        "is_projected": projected,
        "projected_label": projected_label,
    }


def project_dailyplan_result(*, dailyplan, meal, hour, note, current_weight, replaced=None) -> dict:
    before_macros = _macros(dailyplan)
    before_kcal = _kcal(dailyplan)
    replaced_macros = _macros(replaced.meal) if replaced else (0.0, 0.0, 0.0)
    replaced_kcal = _kcal(replaced.meal) if replaced else (0.0, 0.0, 0.0)
    result_macros = _add(_subtract(before_macros, replaced_macros), _macros(meal))
    result_kcal = _add(_subtract(before_kcal, replaced_kcal), _kcal(meal))
    relations = list(
        dailyplan.dailyplan_meals.select_related("meal")
        .prefetch_related("meal__meal_food_set__food")
        .order_by("order", "id")
    )
    rows = [
        _meal_row(
            meal=relation.meal,
            relation_id=relation.id,
            hour=relation.hour,
            note=relation.note,
            parent_kcal=result_kcal,
            current_weight=current_weight,
        )
        for relation in relations
        if not replaced or relation.id != replaced.id
    ]
    rows.append(
        _meal_row(
            meal=meal,
            relation_id=replaced.id if replaced else None,
            hour=hour,
            note=note,
            parent_kcal=result_kcal,
            current_weight=current_weight,
            projected=True,
            projected_label="Reemplazo" if replaced else "Por agregar",
        )
    )
    food_ids = {
        food_id
        for relation in relations
        if not replaced or relation.id != replaced.id
        for food_id in relation.meal.meal_food_set.values_list("food_id", flat=True)
    }
    food_ids.update(meal.meal_food_set.values_list("food_id", flat=True))
    return {
        "id": dailyplan.id,
        "entity": "dailyPlan",
        "name": dailyplan.name,
        "nutrition": _nutrition(result_macros, result_kcal, current_weight),
        "indicators": [
            {"icon": "meal", "label": "comidas", "value": len(rows)},
            {"icon": "food", "label": "alimentos", "value": len(food_ids)},
        ],
        "panel": {"kind": "meals", "foods": [], "meals": rows, "weeks": []},
    }


def project_dailyplan_food_result(
    *, dailyplan, dailyplan_meal, food, quantity, current_weight, replaced=None
) -> dict:
    """Project a food edit inside a DPM as its resulting DailyPlan."""
    meal = dailyplan_meal.meal
    meal_result = project_meal_result(
        meal=meal,
        food=food,
        quantity=quantity,
        current_weight=current_weight,
        replaced=replaced,
    )
    factor = float(quantity) / 100
    selected_macros = tuple(value * factor for value in _macros(food))
    selected_kcal = tuple(value * factor for value in _kcal(food))
    replaced_macros = _macros(replaced) if replaced else (0.0, 0.0, 0.0)
    replaced_kcal = _kcal(replaced) if replaced else (0.0, 0.0, 0.0)
    projected_meal_macros = _add(_subtract(_macros(meal), replaced_macros), selected_macros)
    projected_meal_kcal = _add(_subtract(_kcal(meal), replaced_kcal), selected_kcal)
    result_macros = _add(_subtract(_macros(dailyplan), _macros(meal)), projected_meal_macros)
    result_kcal = _add(_subtract(_kcal(dailyplan), _kcal(meal)), projected_meal_kcal)
    relations = list(
        dailyplan.dailyplan_meals.select_related("meal")
        .prefetch_related("meal__meal_food_set__food")
        .order_by("order", "id")
    )
    rows = [
        _meal_row(
            meal=relation.meal,
            relation_id=relation.id,
            hour=relation.hour,
            note=relation.note,
            parent_kcal=result_kcal,
            current_weight=current_weight,
            projected=relation.id == dailyplan_meal.id,
            projected_label="Actualizada" if relation.id == dailyplan_meal.id else None,
            projected_macros=projected_meal_macros if relation.id == dailyplan_meal.id else None,
            projected_kcal=projected_meal_kcal if relation.id == dailyplan_meal.id else None,
            projected_foods=meal_result["panel"]["foods"] if relation.id == dailyplan_meal.id else None,
        )
        for relation in relations
    ]
    food_ids = {
        relation.food_id
        for slot in relations
        for relation in slot.meal.meal_food_set.all()
        if not (slot.id == dailyplan_meal.id and replaced and relation.id == replaced.id)
    }
    food_ids.add(food.id)
    return {
        "id": dailyplan.id,
        "entity": "dailyPlan",
        "name": dailyplan.name,
        "nutrition": _nutrition(result_macros, result_kcal, current_weight),
        "indicators": [
            {"icon": "meal", "label": "comidas", "value": len(rows)},
            {"icon": "food", "label": "alimentos", "value": len(food_ids)},
        ],
        "panel": {"kind": "meals", "foods": [], "meals": rows, "weeks": []},
    }


def _aggregate_week_foods(day_plans, week_kcal):
    aggregate = defaultdict(lambda: {"food": None, "quantity": 0.0})
    for dailyplan in day_plans.values():
        for slot in dailyplan.dailyplan_meals.all():
            for relation in slot.meal.meal_food_set.all():
                aggregate[relation.food_id]["food"] = relation.food
                aggregate[relation.food_id]["quantity"] += float(relation.quantity)
    return [
        _food_row(
            food=value["food"],
            quantity=value["quantity"],
            relation_id=None,
            parent_kcal=week_kcal,
            row_id=f"projected-week-food:{food_id}",
        )
        for food_id, value in sorted(aggregate.items())
    ]


def project_program_week_result(*, program, dailyplan, week_number, day_numbers, current_weight) -> dict:
    program_days = list(
        ProgramDay.objects.filter(program=program)
        .select_related("dailyplan")
        .prefetch_related("dailyplan__dailyplan_meals__meal__meal_food_set__food")
        .order_by("week_number", "day_number")
    )
    existing_by_slot = {(row.week_number, row.day_number): row for row in program_days}
    selected_days = set(day_numbers)
    projected_plans = {
        day: dailyplan if day in selected_days else existing_by_slot.get((week_number, day)).dailyplan
        for day in range(1, 8)
        if day in selected_days or existing_by_slot.get((week_number, day))
    }
    week_macros = tuple(sum(_macros(plan)[index] for plan in projected_plans.values()) for index in range(3))
    week_kcal = tuple(sum(_kcal(plan)[index] for plan in projected_plans.values()) for index in range(3))
    days = []
    for day_number in range(1, 8):
        plan = projected_plans.get(day_number)
        existing = existing_by_slot.get((week_number, day_number))
        projected = day_number in selected_days
        days.append(
            {
                "id": f"projected-program-week:{program.id}:{week_number}:day:{day_number}",
                "program_day_id": existing.id if existing else None,
                "day_number": day_number,
                "day_label": DAY_LABELS[day_number],
                "dailyplan_id": plan.id if plan else None,
                "plan_name": plan.name if plan else None,
                "nutrition": entity_nutrition(plan, current_weight) if plan else None,
                "meals": [
                    _meal_row(
                        meal=slot.meal,
                        relation_id=slot.id,
                        hour=slot.hour,
                        note=slot.note,
                        parent_kcal=_kcal(plan),
                        current_weight=current_weight,
                    )
                    for slot in plan.dailyplan_meals.all()
                ]
                if plan
                else [],
                "is_projected": projected,
                "projected_label": "Reemplazo" if projected and existing else "Por agregar" if projected else None,
            }
        )
    other_week_kcal = sum(sum(_kcal(row.dailyplan)) for row in program_days if row.week_number != week_number)
    total_program_kcal = other_week_kcal + sum(week_kcal)
    foods = _aggregate_week_foods(projected_plans, week_kcal)
    meals_count = sum(plan.dailyplan_meals.count() for plan in projected_plans.values())
    week = {
        "id": f"projected-program-week:{program.id}:{week_number}",
        "week_number": week_number,
        "days": days,
        "filled_days_count": len(projected_plans),
        "meals_count": meals_count,
        "foods_count": len(foods),
        "average_calories": _number(sum(week_kcal) / len(projected_plans)) if projected_plans else 0.0,
        "foods": foods,
        "calories": _number(sum(week_kcal)),
        "calorie_share": _percentage(sum(week_kcal), total_program_kcal),
        "calorie_distribution": {key: _number(value) for key, value in macro_kcal_distribution(*week_kcal).items()},
        "protein_grams": _number(week_macros[0]),
        "carbs_grams": _number(week_macros[1]),
        "fat_grams": _number(week_macros[2]),
        "protein_allocation": _percentage(week_kcal[0], sum(week_kcal)),
        "carbs_allocation": _percentage(week_kcal[1], sum(week_kcal)),
        "fat_allocation": _percentage(week_kcal[2], sum(week_kcal)),
    }
    return {
        "id": week_number,
        "entity": "week",
        "name": f"Semana {week_number} resultante",
        "nutrition": _nutrition(week_macros, week_kcal, current_weight),
        "indicators": [
            {"icon": "dailyPlan", "label": "planes diarios", "value": len(projected_plans)},
            {"icon": "meal", "label": "comidas", "value": meals_count},
            {"icon": "food", "label": "alimentos", "value": len(foods)},
        ],
        "panel": {"kind": "weeks", "foods": [], "meals": [], "weeks": [week]},
    }
