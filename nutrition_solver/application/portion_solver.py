from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from nutrition_solver.domain.constants import (
    CARBS_KCAL_PER_GRAM,
    FAT_KCAL_PER_GRAM,
    PROTEIN_KCAL_PER_GRAM,
)
from nutrition_solver.domain.models import (
    MacroTarget,
    PortionSolverDiagnostics,
    PortionSolverResult,
    SolvedFoodPortion,
    SolverFood,
)


@dataclass(frozen=True)
class PortionSolverConfig:
    max_iterations: int = 220
    protein_weight: float = 3.0
    carbs_weight: float = 1.35
    fat_weight: float = 1.25
    kcal_weight: float = 2.4
    overshoot_penalty_weight: float = 0.9
    undershoot_penalty_weight: float = 0.45
    optional_food_penalty_weight: float = 0.015


DEFAULT_PORTION_SOLVER_CONFIG = PortionSolverConfig()


class PortionSolverError(ValueError):
    pass


def solve_meal_portions(
    *,
    foods: list[SolverFood],
    target: MacroTarget,
    config: PortionSolverConfig | None = None,
) -> PortionSolverResult:
    """Find human-sized portions for a fixed set of foods.

    Solver v2 remains deterministic and dependency-free, but is less brittle
    than the first coordinate pass: it evaluates several starts, allows
    optional foods to stay at 0 g, and uses a coarse-to-fine local search.
    This preserves the engine boundary needed by chat, MCP and future LLM
    orchestration: fixed candidates + macro target -> portions + diagnostics.
    """
    if not foods:
        raise PortionSolverError("portion_solver_requires_foods")

    config = config or DEFAULT_PORTION_SOLVER_CONFIG
    normalized_foods = [_normalize_food(food) for food in foods if food.required or food.bounds.maximum_g > 0]

    if not normalized_foods:
        raise PortionSolverError("portion_solver_requires_usable_foods")

    best_quantities: dict[int, float] | None = None
    best_score: float | None = None
    best_iterations = 0

    for start in _initial_quantity_sets(foods=normalized_foods, target=target):
        quantities, score, iterations = _optimize_from_start(
            foods=normalized_foods,
            quantities=start,
            target=target,
            config=config,
        )
        if best_score is None or score < best_score:
            best_quantities = quantities
            best_score = score
            best_iterations = iterations

    if best_quantities is None or best_score is None:
        raise PortionSolverError("portion_solver_could_not_initialize")

    portions = [
        SolvedFoodPortion(
            food_id=food.food_id,
            name=food.name,
            role=food.role,
            quantity_g=best_quantities[food.food_id],
            macros=food.macros_for_quantity(best_quantities[food.food_id]),
        )
        for food in normalized_foods
        if best_quantities[food.food_id] > 0
    ]
    actual = _sum_macros(portions)
    diff = _diff_macros(actual=actual, target=target)
    diff_percent = {
        "kcal": _diff_percent(actual.kcal, target.kcal),
        "protein": _diff_percent(actual.protein, target.protein),
        "carbs": _diff_percent(actual.carbs, target.carbs),
        "fat": _diff_percent(actual.fat, target.fat),
    }
    diagnostics = PortionSolverDiagnostics(
        score=best_score,
        iterations=best_iterations,
        target=target,
        actual=actual,
        diff=diff,
        diff_percent=diff_percent,
        notes=_build_notes(actual=actual, target=target, diff_percent=diff_percent),
    )
    return PortionSolverResult(
        portions=portions,
        diagnostics=diagnostics,
    )


def _optimize_from_start(
    *,
    foods: list[SolverFood],
    quantities: dict[int, float],
    target: MacroTarget,
    config: PortionSolverConfig,
) -> tuple[dict[int, float], float, int]:
    quantities = {
        food.food_id: _normalize_quantity(food=food, value=quantities.get(food.food_id, 0.0))
        for food in foods
    }
    best_score = _score_solution(
        foods=foods,
        quantities=quantities,
        target=target,
        config=config,
    )
    iterations = 0
    step_multipliers = (8, 4, 2, 1)

    for iteration in range(config.max_iterations):
        improved = False
        best_candidate = quantities
        best_candidate_score = best_score

        for food in foods:
            bounds = food.bounds.normalized()
            for multiplier in step_multipliers:
                delta = bounds.step_g * multiplier
                for raw_candidate_quantity in (
                    quantities[food.food_id] - delta,
                    quantities[food.food_id] + delta,
                    0.0 if not food.required else bounds.minimum_g,
                    bounds.minimum_g,
                    bounds.maximum_g,
                ):
                    candidate_quantity = _normalize_quantity(
                        food=food,
                        value=raw_candidate_quantity,
                    )

                    if candidate_quantity == quantities[food.food_id]:
                        continue

                    candidate = dict(quantities)
                    candidate[food.food_id] = candidate_quantity
                    candidate_score = _score_solution(
                        foods=foods,
                        quantities=candidate,
                        target=target,
                        config=config,
                    )

                    if candidate_score + 0.0001 < best_candidate_score:
                        best_candidate = candidate
                        best_candidate_score = candidate_score
                        improved = True

        iterations = iteration + 1
        if not improved:
            break

        quantities = best_candidate
        best_score = best_candidate_score

    return quantities, best_score, iterations


def _initial_quantity_sets(*, foods: list[SolverFood], target: MacroTarget) -> list[dict[int, float]]:
    starts: list[dict[int, float]] = []
    role_start = {
        food.food_id: _initial_quantity(food=food, target=target)
        for food in foods
    }
    starts.append(role_start)
    starts.append(
        {
            food.food_id: _normalize_quantity(
                food=food,
                value=food.bounds.normalized().minimum_g if food.required else 0.0,
            )
            for food in foods
        }
    )
    starts.append(
        {
            food.food_id: _normalize_quantity(
                food=food,
                value=(food.bounds.normalized().minimum_g + food.bounds.normalized().maximum_g) / 2,
            )
            for food in foods
        }
    )
    starts.append(
        {
            food.food_id: _normalize_quantity(
                food=food,
                value=food.bounds.normalized().maximum_g,
            )
            for food in foods
        }
    )

    # Add one sparse start per optional food. This lets the solver discover
    # useful fats/vegetables without forcing every optional role into every meal.
    for optional_food in [food for food in foods if not food.required]:
        sparse = {
            food.food_id: _normalize_quantity(
                food=food,
                value=food.bounds.normalized().minimum_g if food.required else 0.0,
            )
            for food in foods
        }
        sparse[optional_food.food_id] = _normalize_quantity(
            food=optional_food,
            value=_initial_quantity(food=optional_food, target=target),
        )
        starts.append(sparse)

    unique_starts: list[dict[int, float]] = []
    seen = set()
    for start in starts:
        key = tuple(sorted(start.items()))
        if key in seen:
            continue
        seen.add(key)
        unique_starts.append(start)
    return unique_starts


def _normalize_food(food: SolverFood) -> SolverFood:
    bounds = food.bounds.normalized()
    if food.kcal_per_100g <= 0:
        inferred_kcal = (
            food.protein_per_100g * PROTEIN_KCAL_PER_GRAM
            + food.carbs_per_100g * CARBS_KCAL_PER_GRAM
            + food.fat_per_100g * FAT_KCAL_PER_GRAM
        )
        return SolverFood(
            food_id=food.food_id,
            name=food.name,
            role=food.role,
            protein_per_100g=food.protein_per_100g,
            carbs_per_100g=food.carbs_per_100g,
            fat_per_100g=food.fat_per_100g,
            kcal_per_100g=inferred_kcal,
            bounds=bounds,
            required=food.required,
        )

    return SolverFood(
        food_id=food.food_id,
        name=food.name,
        role=food.role,
        protein_per_100g=food.protein_per_100g,
        carbs_per_100g=food.carbs_per_100g,
        fat_per_100g=food.fat_per_100g,
        kcal_per_100g=food.kcal_per_100g,
        bounds=bounds,
        required=food.required,
    )


def _initial_quantity(*, food: SolverFood, target: MacroTarget) -> float:
    bounds = food.bounds.normalized()
    role = food.role

    if role == "protein" and food.protein_per_100g > 0:
        raw_quantity = target.protein / food.protein_per_100g * 100
    elif role == "carb" and food.carbs_per_100g > 0:
        raw_quantity = target.carbs / food.carbs_per_100g * 100
    elif role == "fat" and food.fat_per_100g > 0:
        raw_quantity = target.fat / food.fat_per_100g * 100
    elif role == "vegetable":
        raw_quantity = min(max(100, bounds.minimum_g), bounds.maximum_g)
    elif food.kcal_per_100g > 0:
        raw_quantity = target.kcal / max(len(role), 1) / food.kcal_per_100g * 100
    else:
        raw_quantity = bounds.minimum_g if food.required else 0.0

    return _normalize_quantity(food=food, value=raw_quantity)


def _score_solution(
    *,
    foods: list[SolverFood],
    quantities: dict[int, float],
    target: MacroTarget,
    config: PortionSolverConfig,
) -> float:
    portions = [
        SolvedFoodPortion(
            food_id=food.food_id,
            name=food.name,
            role=food.role,
            quantity_g=quantities[food.food_id],
            macros=food.macros_for_quantity(quantities[food.food_id]),
        )
        for food in foods
        if quantities[food.food_id] > 0
    ]
    actual = _sum_macros(portions)
    weighted_error = (
        config.kcal_weight * _relative_squared_error(actual.kcal, target.kcal)
        + config.protein_weight * _relative_squared_error(actual.protein, target.protein)
        + config.carbs_weight * _relative_squared_error(actual.carbs, target.carbs)
        + config.fat_weight * _relative_squared_error(actual.fat, target.fat)
    )
    overshoot_penalty = (
        _positive_relative_error(actual.kcal, target.kcal)
        + _positive_relative_error(actual.protein, target.protein) * 0.35
        + _positive_relative_error(actual.fat, target.fat) * 0.25
    )
    undershoot_penalty = (
        _negative_relative_error(actual.kcal, target.kcal) * 0.45
        + _negative_relative_error(actual.protein, target.protein) * 0.8
    )
    optional_food_penalty = sum(
        1 for food in foods if not food.required and quantities.get(food.food_id, 0) > 0
    )
    required_missing_penalty = sum(
        10 for food in foods if food.required and quantities.get(food.food_id, 0) <= 0
    )
    return (
        weighted_error
        + config.overshoot_penalty_weight * overshoot_penalty
        + config.undershoot_penalty_weight * undershoot_penalty
        + config.optional_food_penalty_weight * optional_food_penalty
        + required_missing_penalty
    )


def _sum_macros(portions: list[SolvedFoodPortion]) -> MacroTarget:
    return MacroTarget(
        kcal=sum(portion.macros.kcal for portion in portions),
        protein=sum(portion.macros.protein for portion in portions),
        carbs=sum(portion.macros.carbs for portion in portions),
        fat=sum(portion.macros.fat for portion in portions),
    )


def _diff_macros(*, actual: MacroTarget, target: MacroTarget) -> MacroTarget:
    return MacroTarget(
        kcal=actual.kcal - target.kcal,
        protein=actual.protein - target.protein,
        carbs=actual.carbs - target.carbs,
        fat=actual.fat - target.fat,
    )


def _relative_squared_error(actual: float, target: float) -> float:
    target = max(abs(float(target)), 1.0)
    return ((float(actual) - float(target)) / target) ** 2


def _positive_relative_error(actual: float, target: float) -> float:
    if actual <= target:
        return 0.0
    target = max(abs(float(target)), 1.0)
    return (float(actual) - float(target)) / target


def _negative_relative_error(actual: float, target: float) -> float:
    if actual >= target:
        return 0.0
    target = max(abs(float(target)), 1.0)
    return (float(target) - float(actual)) / target


def _diff_percent(actual: float, target: float) -> float | None:
    if not target:
        return None
    value = ((float(actual) - float(target)) / float(target)) * 100
    if not isfinite(value):
        return None
    return value


def _build_notes(*, actual: MacroTarget, target: MacroTarget, diff_percent: dict[str, float | None]) -> list[str]:
    notes = []
    kcal_diff = abs(diff_percent.get("kcal") or 0)
    protein_diff = abs(diff_percent.get("protein") or 0)
    carbs_diff = abs(diff_percent.get("carbs") or 0)
    fat_diff = abs(diff_percent.get("fat") or 0)

    if kcal_diff <= 5:
        notes.append("Kcal dentro de una tolerancia inicial razonable.")
    else:
        notes.append("Kcal fuera de tolerancia inicial; revisar candidatos o rangos de porción.")

    if protein_diff <= 10:
        notes.append("Proteína cercana al objetivo inicial.")
    else:
        notes.append("Proteína fuera de tolerancia inicial; revisar fuente proteica o objetivo.")

    if carbs_diff > 15:
        notes.append("Carbohidratos fuera de tolerancia inicial; revisar fuente de carbohidratos o distribución por comida.")

    if fat_diff > 15:
        notes.append("Grasa fuera de tolerancia inicial; revisar fuente de grasa o límites de porción.")

    return notes


def _normalize_quantity(*, food: SolverFood, value: float) -> float:
    bounds = food.bounds.normalized()

    if not food.required and float(value) <= 0:
        return 0.0

    minimum = bounds.minimum_g if food.required or float(value) > 0 else 0.0
    return _round_to_step(
        _clamp(float(value), minimum, bounds.maximum_g),
        bounds.step_g,
    )


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(float(minimum), min(float(value), float(maximum)))


def _round_to_step(value: float, step: float) -> float:
    step = max(float(step or 1), 1.0)
    return float(round(float(value) / step) * step)
