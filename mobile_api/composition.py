"""Screen-oriented mobile composition pickers.

The transport layer stays deliberately small: ownership and picker availability
are resolved here, while every write delegates to the same commands used by the
responsive web application.
"""

from __future__ import annotations

from django.db import transaction

from mobile_api.composition_projections import (
    project_dailyplan_food_result,
    project_dailyplan_result,
    project_meal_result,
    project_program_week_result,
)
from mobile_api.errors import MobileAPIError
from notas.application.queries.read_boundaries import get_readable_food_queryset
from notas.application.services.commands.dailyplan_commands import (
    add_existing_meal_to_dailyplan,
    remove_dailyplan_meal,
    reorder_dailyplan_meals,
    update_dailyplan_meal,
)
from notas.application.services.commands.meal_commands import (
    create_meal_food,
    delete_meal_food,
    reorder_meal_foods,
    update_meal_food,
)
from notas.application.services.commands.program_commands import (
    add_week_to_program,
    assign_dailyplan_to_program_slot,
    duplicate_week_in_program,
    remove_program_day,
    remove_week_from_program,
    reorder_program_weeks,
)
from notas.application.services.food_imports.localized_names import resolve_food_display_name
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood, Program, ProgramDay

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


def _entity_macros(entity) -> tuple[float, float, float]:
    return float(entity.protein or 0), float(entity.carbs or 0), float(entity.fat or 0)


def _nutrition(protein: float, carbs: float, fat: float, current_weight) -> dict:
    protein_kcal = protein * 4
    carbs_kcal = carbs * 4
    fat_kcal = fat * 9
    calories = protein_kcal + carbs_kcal + fat_kcal

    def allocation(value: float) -> float:
        return _number(value / calories * 100) if calories > 0 else 0.0

    return {
        "calories": _number(calories),
        "protein": {
            "grams": _number(protein),
            "allocation": allocation(protein_kcal),
            "per_kilogram": _number(protein / current_weight) if current_weight and protein else None,
        },
        "carbs": {"grams": _number(carbs), "allocation": allocation(carbs_kcal)},
        "fat": {"grams": _number(fat), "allocation": allocation(fat_kcal)},
    }


def _entity_nutrition(entity, current_weight) -> dict:
    return _nutrition(*_entity_macros(entity), current_weight)


def _selection(*, item_id: int, entity: str, name: str, nutrition=None, quantity=None, hour=None) -> dict:
    return {
        "id": item_id,
        "entity": entity,
        "name": name,
        "nutrition": nutrition,
        "quantity": quantity,
        "hour": hour,
    }


def _impact(*, label: str, entity: str, before: dict, after: dict, metrics=None) -> dict:
    return {
        "label": label,
        "entity": entity,
        "before": before,
        "after": after,
        "metrics": metrics or [],
    }


def _owned_meal(user, meal_id: int) -> Meal:
    meal = Meal.objects.filter(pk=meal_id, created_by=user).first()
    if not meal:
        raise MobileAPIError("picker_target_not_found", "La comida no está disponible para edición.", 404)
    return meal


def _owned_dailyplan(user, dailyplan_id: int) -> DailyPlan:
    dailyplan = (
        DailyPlan.objects.filter(pk=dailyplan_id, created_by=user).exclude(source=DailyPlan.SOURCE_PROGRAM).first()
    )
    if not dailyplan:
        raise MobileAPIError("picker_target_not_found", "El plan diario no está disponible para edición.", 404)
    return dailyplan


def _owned_program(user, program_id: int) -> Program:
    program = Program.objects.filter(pk=program_id, created_by=user).first()
    if not program:
        raise MobileAPIError("picker_target_not_found", "El programa no está disponible para edición.", 404)
    return program


def _readable_food(user, food_id: int) -> Food:
    food = get_readable_food_queryset(user).filter(pk=food_id, is_active=True).first()
    if not food:
        raise MobileAPIError("picker_selection_not_found", "El alimento seleccionado no está disponible.", 404)
    return food


def _library_meal(user, meal_id: int) -> Meal:
    meal = Meal.objects.filter(
        pk=meal_id,
        created_by=user,
        is_draft=False,
        dailyplanmeal__isnull=True,
    ).first()
    if not meal:
        raise MobileAPIError("picker_selection_not_found", "La comida seleccionada no está disponible.", 404)
    return meal


def _library_dailyplan(user, dailyplan_id: int) -> DailyPlan:
    dailyplan = (
        DailyPlan.objects.filter(pk=dailyplan_id, created_by=user, is_draft=False)
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .first()
    )
    if not dailyplan:
        raise MobileAPIError("picker_selection_not_found", "El plan diario seleccionado no está disponible.", 404)
    return dailyplan


def _positive_quantity(quantity) -> float:
    value = float(quantity or 0)
    if value <= 0:
        raise MobileAPIError("picker_quantity_invalid", "La porción debe ser mayor que cero.", 422)
    return value


def preview_food_for_meal(
    *, user, meal_id: int, food_id: int, quantity, meal_food_id=None,
    dailyplan_id=None, dailyplan_meal_id=None,
) -> dict:
    meal = _owned_meal(user, meal_id)
    food = _readable_food(user, food_id)
    quantity_value = _positive_quantity(quantity)
    current_weight = get_current_weight(user)
    meal_macros = _entity_macros(meal)
    food_macros = tuple(value * quantity_value / 100 for value in _entity_macros(food))
    replaced = _owned_meal_food(user, meal_id, meal_food_id)[1] if meal_food_id else None
    meal_result = project_meal_result(
        meal=meal,
        food=food,
        quantity=quantity_value,
        current_weight=current_weight,
        replaced=replaced,
    )
    dailyplan = None
    dailyplan_meal = None
    if dailyplan_id is not None or dailyplan_meal_id is not None:
        if dailyplan_id is None or dailyplan_meal_id is None:
            raise MobileAPIError("picker_context_invalid", "El contexto del plan diario está incompleto.", 422)
        dailyplan = _owned_dailyplan(user, dailyplan_id)
        dailyplan_meal = _owned_dailyplan_meal(user, dailyplan, dailyplan_meal_id)
        if dailyplan_meal.meal_id != meal.id:
            raise MobileAPIError("picker_context_invalid", "La comida no pertenece al plan diario indicado.", 422)
    result = (
        project_dailyplan_food_result(
            dailyplan=dailyplan,
            dailyplan_meal=dailyplan_meal,
            food=food,
            quantity=quantity_value,
            current_weight=current_weight,
            replaced=replaced,
        )
        if dailyplan and dailyplan_meal
        else meal_result
    )
    before_nutrition = _entity_nutrition(dailyplan, current_weight) if dailyplan else _nutrition(*meal_macros, current_weight)
    return {
        "selection": _selection(
            item_id=food.id,
            entity="food",
            name=resolve_food_display_name(food),
            nutrition=_nutrition(*food_macros, current_weight),
            quantity=_number(quantity_value),
        ),
        "impacts": [
            _impact(
                label=("Plan diario después de reemplazar" if replaced else "Plan diario después de agregar") if dailyplan else ("Comida después de reemplazar" if replaced else "Comida después de agregar"),
                entity="dailyPlan" if dailyplan else "meal",
                before=before_nutrition,
                after=result["nutrition"],
            )
        ],
        "result": result,
        "replacements": [],
        "confirmation_required": False,
    }


def add_food_from_picker(*, user, meal_id: int, food_id: int, quantity, meal_food_id=None) -> dict:
    meal = _owned_meal(user, meal_id)
    food = _readable_food(user, food_id)
    quantity_value = _positive_quantity(quantity)
    if meal_food_id:
        _meal, meal_food = _owned_meal_food(user, meal_id, meal_food_id)
        result = update_meal_food(meal_food=meal_food, quantity=quantity_value, food_id=food.id)
        return {
            "message": "Alimento reemplazado en la comida.",
            "target_id": meal.id,
            "created_id": result.meal_food.id,
        }
    result = create_meal_food(meal=meal, food=food, quantity=quantity_value)
    return {
        "message": "Alimento agregado a la comida.",
        "target_id": meal.id,
        "created_id": result.meal_food.id,
    }


def _owned_dailyplan_meal(user, dailyplan: DailyPlan, dailyplan_meal_id: int) -> DailyPlanMeal:
    dailyplan_meal = (
        DailyPlanMeal.objects.select_related("meal")
        .filter(pk=dailyplan_meal_id, dailyplan=dailyplan, dailyplan__created_by=user)
        .first()
    )
    if not dailyplan_meal:
        raise MobileAPIError("composition_item_not_found", "La comida del plan no está disponible para edición.", 404)
    return dailyplan_meal


def preview_meal_for_dailyplan(
    *, user, dailyplan_id: int, meal_id: int, dailyplan_meal_id=None, hour=None, note=None
) -> dict:
    dailyplan = _owned_dailyplan(user, dailyplan_id)
    meal = _library_meal(user, meal_id)
    current_weight = get_current_weight(user)
    dailyplan_macros = _entity_macros(dailyplan)
    meal_macros = _entity_macros(meal)
    replaced = _owned_dailyplan_meal(user, dailyplan, dailyplan_meal_id) if dailyplan_meal_id else None
    result = project_dailyplan_result(
        dailyplan=dailyplan,
        meal=meal,
        hour=hour,
        note=note,
        current_weight=current_weight,
        replaced=replaced,
    )
    return {
        "selection": _selection(
            item_id=meal.id,
            entity="meal",
            name=meal.name,
            nutrition=_nutrition(*meal_macros, current_weight),
            hour=str(hour)[:5] if hour else None,
        ),
        "impacts": [
            _impact(
                label="Plan diario después de reemplazar" if replaced else "Plan diario después de agregar",
                entity="dailyPlan",
                before=_nutrition(*dailyplan_macros, current_weight),
                after=result["nutrition"],
            )
        ],
        "result": result,
        "replacements": [],
        "confirmation_required": False,
    }


def add_meal_from_picker(
    *, user, dailyplan_id: int, meal_id: int, dailyplan_meal_id=None, hour=None, note=None
) -> dict:
    dailyplan = _owned_dailyplan(user, dailyplan_id)
    meal = _library_meal(user, meal_id)
    if dailyplan_meal_id:
        dailyplan_meal = _owned_dailyplan_meal(user, dailyplan, dailyplan_meal_id)
        result = update_dailyplan_meal(
            dailyplan_meal=dailyplan_meal,
            user=user,
            meal_id=meal.id,
            hour=hour,
            note=note,
        )
        return {
            "message": "Comida reemplazada en el plan diario.",
            "target_id": dailyplan.id,
            "created_id": result.dailyplan_meal.id,
        }
    result = add_existing_meal_to_dailyplan(
        dailyplan=dailyplan,
        meal=meal,
        user=user,
        hour=hour,
        note=note,
    )
    return {
        "message": "Comida agregada al plan diario.",
        "target_id": dailyplan.id,
        "created_id": result.dailyplan_meal.id,
    }


def _program_selection_context(*, user, program_id: int, dailyplan_id: int, week_number, day_numbers):
    program = _owned_program(user, program_id)
    dailyplan = _library_dailyplan(user, dailyplan_id)
    try:
        week = int(week_number)
        days = sorted({int(day) for day in day_numbers})
    except (TypeError, ValueError):
        raise MobileAPIError("picker_slot_invalid", "La semana o los días seleccionados no son válidos.", 422)
    if week < 1 or week > program.normalized_duration_weeks or not days or any(day < 1 or day > 7 for day in days):
        raise MobileAPIError("picker_slot_invalid", "La semana o los días seleccionados no son válidos.", 422)
    existing = {
        row.day_number: row
        for row in ProgramDay.objects.select_related("dailyplan").filter(
            program=program,
            week_number=week,
            day_number__in=days,
        )
    }
    return program, dailyplan, week, days, existing


def preview_dailyplan_for_program(*, user, program_id: int, dailyplan_id: int, week_number, day_numbers) -> dict:
    program, dailyplan, week, days, existing = _program_selection_context(
        user=user,
        program_id=program_id,
        dailyplan_id=dailyplan_id,
        week_number=week_number,
        day_numbers=day_numbers,
    )
    current_weight = get_current_weight(user)
    selected_macros = _entity_macros(dailyplan)
    replacements = [DAY_LABELS[day] for day in days if day in existing]
    result = project_program_week_result(
        program=program,
        dailyplan=dailyplan,
        week_number=week,
        day_numbers=days,
        current_weight=current_weight,
    )
    return {
        "selection": _selection(
            item_id=dailyplan.id,
            entity="dailyPlan",
            name=dailyplan.name,
            nutrition=_nutrition(*selected_macros, current_weight),
        ),
        "impacts": [],
        "result": result,
        "replacements": replacements,
        "confirmation_required": bool(replacements),
    }


@transaction.atomic
def add_dailyplan_from_picker(
    *, user, program_id: int, dailyplan_id: int, week_number, day_numbers, confirm_replacements=False
) -> dict:
    program, dailyplan, week, days, existing = _program_selection_context(
        user=user,
        program_id=program_id,
        dailyplan_id=dailyplan_id,
        week_number=week_number,
        day_numbers=day_numbers,
    )
    replaced_days = [DAY_LABELS[day] for day in days if day in existing]
    if replaced_days and not confirm_replacements:
        raise MobileAPIError(
            "picker_replacement_confirmation_required",
            "Debes confirmar el reemplazo de los días ocupados.",
            409,
            {"replacements": replaced_days},
        )
    created_ids = []
    for day in days:
        result = assign_dailyplan_to_program_slot(
            program=program,
            source_dailyplan=dailyplan,
            user=user,
            week_number=week,
            day_number=day,
        )
        created_ids.append(result.program_day.id)
    if program.is_draft:
        program.is_draft = False
        program.save(update_fields=["is_draft"])
    return {
        "message": "Plan diario asignado a la semana.",
        "target_id": program.id,
        "created_id": created_ids[0],
    }


def preview_week_for_program(*, user, program_id: int) -> dict:
    program = _owned_program(user, program_id)
    current_weight = get_current_weight(user)
    before = _entity_nutrition(program, current_weight)
    current_weeks = program.normalized_duration_weeks
    return {
        "selection": _selection(
            item_id=current_weeks + 1,
            entity="week",
            name=f"Semana {current_weeks + 1}",
        ),
        "impacts": [
            _impact(
                label="Programa completo",
                entity="program",
                before=before,
                after=before,
                metrics=[{"label": "semanas", "before": current_weeks, "after": current_weeks + 1}],
            )
        ],
        "replacements": [],
        "confirmation_required": False,
    }


@transaction.atomic
def add_week_from_picker(*, user, program_id: int, expected_week_number=None) -> dict:
    owned_program = _owned_program(user, program_id)
    program = Program.objects.select_for_update().get(pk=owned_program.pk)
    current_weeks = program.normalized_duration_weeks
    if expected_week_number is not None:
        try:
            expected_week = int(expected_week_number)
        except (TypeError, ValueError) as exc:
            raise MobileAPIError("picker_week_invalid", "La nueva semana no es válida.", 422) from exc
        if expected_week <= current_weeks:
            return {
                "message": f"Semana {expected_week} lista para configurar.",
                "target_id": program.id,
                "created_id": expected_week,
            }
        if expected_week != current_weeks + 1:
            raise MobileAPIError("picker_week_conflict", "El programa cambió antes de crear la semana.", 409)
    add_week_to_program(program=program)
    return {
        "message": f"Semana {program.normalized_duration_weeks} agregada al programa.",
        "target_id": program.id,
        "created_id": program.normalized_duration_weeks,
    }


def _owned_meal_food(user, meal_id: int, meal_food_id: int) -> tuple[Meal, MealFood]:
    meal = _owned_meal(user, meal_id)
    meal_food = MealFood.objects.filter(pk=meal_food_id, meal=meal).first()
    if not meal_food:
        raise MobileAPIError("composition_item_not_found", "El alimento no está disponible para edición.", 404)
    return meal, meal_food


def update_food_in_meal(*, user, meal_id: int, meal_food_id: int, quantity) -> dict:
    meal, meal_food = _owned_meal_food(user, meal_id, meal_food_id)
    update_meal_food(meal_food=meal_food, quantity=_positive_quantity(quantity))
    return {"message": "Porción actualizada.", "target_id": meal.id, "affected_id": meal_food.id}


def remove_food_from_meal(*, user, meal_id: int, meal_food_id: int) -> dict:
    meal, meal_food = _owned_meal_food(user, meal_id, meal_food_id)
    delete_meal_food(meal_food=meal_food)
    return {"message": "Alimento eliminado de la comida.", "target_id": meal.id, "affected_id": meal_food_id}


def reorder_foods_in_meal(*, user, meal_id: int, ordered_ids) -> dict:
    meal = _owned_meal(user, meal_id)
    expected = set(meal.meal_food_set.values_list("id", flat=True))
    ordered = [int(value) for value in ordered_ids]
    if len(ordered) != len(set(ordered)) or set(ordered) != expected:
        raise MobileAPIError("composition_order_invalid", "El orden de alimentos no es válido.", 422)
    reorder_meal_foods(meal=meal, ordered_ids=ordered)
    return {"message": "Orden de alimentos guardado.", "target_id": meal.id, "affected_id": meal.id}


def update_meal_in_dailyplan(*, user, dailyplan_id: int, dailyplan_meal_id: int, hour=None, note=None) -> dict:
    dailyplan = _owned_dailyplan(user, dailyplan_id)
    dailyplan_meal = _owned_dailyplan_meal(user, dailyplan, dailyplan_meal_id)
    update_dailyplan_meal(
        dailyplan_meal=dailyplan_meal,
        user=user,
        hour=dailyplan_meal.hour if hour is None else hour,
        note=dailyplan_meal.note if note is None else note,
    )
    return {"message": "Horario de la comida actualizado.", "target_id": dailyplan.id, "affected_id": dailyplan_meal.id}


def remove_meal_from_dailyplan(*, user, dailyplan_id: int, dailyplan_meal_id: int) -> dict:
    dailyplan = _owned_dailyplan(user, dailyplan_id)
    dailyplan_meal = _owned_dailyplan_meal(user, dailyplan, dailyplan_meal_id)
    remove_dailyplan_meal(dailyplan_meal=dailyplan_meal)
    return {"message": "Comida eliminada del plan diario.", "target_id": dailyplan.id, "affected_id": dailyplan_meal_id}


def reorder_meals_in_dailyplan(*, user, dailyplan_id: int, ordered_ids) -> dict:
    dailyplan = _owned_dailyplan(user, dailyplan_id)
    expected = set(dailyplan.dailyplan_meals.values_list("id", flat=True))
    ordered = [int(value) for value in ordered_ids]
    if len(ordered) != len(set(ordered)) or set(ordered) != expected:
        raise MobileAPIError("composition_order_invalid", "El orden de comidas no es válido.", 422)
    reorder_dailyplan_meals(dailyplan=dailyplan, ordered_ids=ordered)
    return {"message": "Orden de comidas guardado.", "target_id": dailyplan.id, "affected_id": dailyplan.id}


def reorder_weeks_in_program(*, user, program_id: int, ordered_weeks) -> dict:
    program = _owned_program(user, program_id)
    try:
        reorder_program_weeks(program=program, ordered_week_numbers=ordered_weeks)
    except ValueError as exc:
        raise MobileAPIError("composition_order_invalid", "El orden de semanas no es válido.", 422) from exc
    return {"message": "Orden de semanas guardado.", "target_id": program.id, "affected_id": program.id}


def duplicate_program_week(*, user, program_id: int, week_number: int) -> dict:
    program = _owned_program(user, program_id)
    try:
        result = duplicate_week_in_program(program=program, week_number=week_number, user=user)
    except ValueError as exc:
        raise MobileAPIError("composition_week_invalid", "La semana no está disponible.", 422) from exc
    return {
        "message": f"Semana {result.source_week_number} duplicada.",
        "target_id": program.id,
        "affected_id": result.new_week_number,
    }


def remove_program_week(*, user, program_id: int, week_number: int) -> dict:
    program = _owned_program(user, program_id)
    try:
        remove_week_from_program(program=program, week_number=week_number)
    except ValueError as exc:
        message = (
            "El programa debe conservar al menos una semana."
            if str(exc) == "program_cannot_remove_last_week"
            else "La semana no está disponible."
        )
        raise MobileAPIError("composition_week_invalid", message, 422) from exc
    return {"message": f"Semana {week_number} eliminada.", "target_id": program.id, "affected_id": week_number}


def remove_dailyplan_from_program(*, user, program_id: int, week_number: int, day_number: int) -> dict:
    program = _owned_program(user, program_id)
    program_day = ProgramDay.objects.filter(program=program, week_number=week_number, day_number=day_number).first()
    if not program_day:
        raise MobileAPIError("composition_item_not_found", "El día no tiene un plan asignado.", 404)
    program_day_id = program_day.id
    remove_program_day(program_day=program_day)
    return {"message": "Plan diario eliminado de la semana.", "target_id": program.id, "affected_id": program_day_id}
