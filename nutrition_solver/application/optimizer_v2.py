from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import ceil, floor
from typing import Any, Mapping

from nutrition_solver.application.candidate_portfolio import build_candidate_portfolio
from nutrition_solver.application.contracts import OptimizationStatus
from nutrition_solver.application.portion_solver import PortionSolverError, solve_meal_portions
from nutrition_solver.application.problem_v2 import MealSlotProblem, NutrientRange, OptimizationProblemV2
from nutrition_solver.domain.models import MacroTarget


class OptimizationBackend(str, Enum):
    HEURISTIC_V2 = "heuristic_v2"
    CP_SAT_V1 = "cp_sat_v1"


@dataclass(frozen=True)
class SelectedPortionV2:
    slot_id: str
    food_id: int
    name: str
    quantity_g: float
    nutrients: Mapping[str, float]
    functional_roles: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "food_id": self.food_id,
            "name": self.name,
            "quantity_g": round(self.quantity_g, 2),
            "nutrients": {key: round(value, 2) for key, value in self.nutrients.items()},
            "functional_roles": list(self.functional_roles),
        }


@dataclass(frozen=True)
class MealSolutionV2:
    slot_id: str
    archetype: str
    portions: tuple[SelectedPortionV2, ...]
    nutrient_totals: Mapping[str, float]

    def as_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "archetype": self.archetype,
            "portions": [portion.as_dict() for portion in self.portions],
            "nutrient_totals": {
                key: round(value, 2) for key, value in self.nutrient_totals.items()
            },
        }


@dataclass(frozen=True)
class OptimizationPlanResultV2:
    backend: OptimizationBackend
    status: OptimizationStatus
    objective_value: float
    meals: tuple[MealSolutionV2, ...] = ()
    daily_totals: Mapping[str, float] = field(default_factory=dict)
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "backend", OptimizationBackend(self.backend))
        object.__setattr__(self, "status", OptimizationStatus(self.status))
        object.__setattr__(self, "meals", tuple(self.meals or ()))
        object.__setattr__(self, "daily_totals", dict(self.daily_totals or {}))
        object.__setattr__(self, "diagnostics", dict(self.diagnostics or {}))

    def as_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend.value,
            "status": self.status.value,
            "objective_value": round(self.objective_value, 4),
            "meals": [meal.as_dict() for meal in self.meals],
            "daily_totals": {
                key: round(value, 2) for key, value in self.daily_totals.items()
            },
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(frozen=True)
class OptimizationAlternativesV2:
    backend: OptimizationBackend
    alternatives: tuple[OptimizationPlanResultV2, ...]
    requested_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend.value,
            "requested_count": self.requested_count,
            "alternatives": [alternative.as_dict() for alternative in self.alternatives],
        }


def solve_optimization_problem(
    problem: OptimizationProblemV2,
    *,
    backend: OptimizationBackend | str = OptimizationBackend.HEURISTIC_V2,
) -> OptimizationPlanResultV2:
    selected_backend = OptimizationBackend(backend)
    if selected_backend == OptimizationBackend.CP_SAT_V1:
        return _solve_cp_sat(problem, forbidden_selections=())
    return _solve_heuristic(problem)


def solve_optimization_alternatives(
    problem: OptimizationProblemV2,
    *,
    count: int = 3,
    backend: OptimizationBackend | str = OptimizationBackend.CP_SAT_V1,
) -> OptimizationAlternativesV2:
    """Return distinct selected-food compositions ordered by solver objective."""

    selected_backend = OptimizationBackend(backend)
    requested = max(1, min(int(count), 10))
    if selected_backend != OptimizationBackend.CP_SAT_V1:
        result = solve_optimization_problem(problem, backend=selected_backend)
        alternatives = () if result.status == OptimizationStatus.IMPOSSIBLE else (result,)
        return OptimizationAlternativesV2(selected_backend, alternatives, requested)

    alternatives: list[OptimizationPlanResultV2] = []
    forbidden: list[tuple[tuple[str, int], ...]] = []
    for _ in range(requested):
        result = _solve_cp_sat(problem, forbidden_selections=tuple(forbidden))
        if result.status == OptimizationStatus.IMPOSSIBLE:
            break
        alternatives.append(result)
        forbidden.append(_selection_signature(result))
    return OptimizationAlternativesV2(selected_backend, tuple(alternatives), requested)


def _solve_heuristic(problem: OptimizationProblemV2) -> OptimizationPlanResultV2:
    meals: list[MealSolutionV2] = []
    for slot in problem.meal_slots:
        archetype = slot.allowed_archetypes[0]
        portfolio = build_candidate_portfolio(
            problem.food_profiles,
            archetype,
            meal_kind=slot.meal_kind,
            excluded_food_ids=_excluded_food_ids(problem),
            preferred_food_ids=tuple(problem.preferences.get("preferred_food_ids", ())),
        )
        if not portfolio.combinations:
            return _impossible_result(OptimizationBackend.HEURISTIC_V2, "candidate_portfolio_empty")
        target = _macro_target(slot.nutrient_ranges)
        try:
            result = solve_meal_portions(
                foods=[profile.food for profile in portfolio.combinations[0].profiles],
                target=target,
            )
        except PortionSolverError as exc:
            return _impossible_result(OptimizationBackend.HEURISTIC_V2, str(exc))
        portions = tuple(
            SelectedPortionV2(
                slot_id=slot.slot_id,
                food_id=portion.food_id,
                name=portion.name,
                quantity_g=portion.quantity_g,
                nutrients=portion.macros.as_dict(),
                functional_roles=next(
                    profile.functional_roles
                    for profile in portfolio.combinations[0].profiles
                    if profile.food.food_id == portion.food_id
                ),
            )
            for portion in result.portions
        )
        meals.append(
            MealSolutionV2(
                slot_id=slot.slot_id,
                archetype=archetype.key,
                portions=portions,
                nutrient_totals=result.diagnostics.actual.as_dict(),
            )
        )
    return OptimizationPlanResultV2(
        backend=OptimizationBackend.HEURISTIC_V2,
        status=OptimizationStatus.ACCEPTABLE,
        objective_value=sum(meal_value for meal_value in (0.0 for _ in meals)),
        meals=tuple(meals),
        daily_totals=_sum_meal_totals(meals),
        diagnostics={"solver_status": "heuristic_complete"},
    )


def _solve_cp_sat(
    problem: OptimizationProblemV2,
    *,
    forbidden_selections: tuple[tuple[tuple[str, int], ...], ...],
) -> OptimizationPlanResultV2:
    from ortools.sat.python import cp_model

    model = cp_model.CpModel()
    profiles = tuple(sorted(problem.food_profiles, key=lambda item: item.food.food_id))
    excluded = _excluded_food_ids(problem)
    quantity_steps = {}
    selected = {}
    slot_archetypes = {}

    for slot in problem.meal_slots:
        archetype = slot.allowed_archetypes[0]
        slot_archetypes[slot.slot_id] = archetype
        for profile in profiles:
            food = profile.food
            bounds = food.bounds.normalized()
            minimum_steps = max(1, ceil(bounds.minimum_g / bounds.step_g))
            maximum_steps = max(0, floor(bounds.maximum_g / bounds.step_g))
            y = model.new_bool_var(f"selected_{slot.slot_id}_{food.food_id}")
            q = model.new_int_var(0, maximum_steps, f"steps_{slot.slot_id}_{food.food_id}")
            selected[slot.slot_id, food.food_id] = y
            quantity_steps[slot.slot_id, food.food_id] = q
            model.add(q >= minimum_steps * y)
            model.add(q <= maximum_steps * y)
            if food.food_id in excluded or maximum_steps < minimum_steps:
                model.add(y == 0)

        slot_selected = [selected[slot.slot_id, profile.food.food_id] for profile in profiles]
        model.add(sum(slot_selected) >= archetype.minimum_components)
        model.add(sum(slot_selected) <= archetype.maximum_components)
        for role_group in archetype.required_role_groups:
            coverage = [
                selected[slot.slot_id, profile.food.food_id]
                for profile in profiles
                if set(profile.functional_roles).intersection(role_group)
            ]
            if not coverage:
                return _impossible_result(OptimizationBackend.CP_SAT_V1, "required_role_group_empty")
            model.add(sum(coverage) >= 1)

    for food_id in _required_food_ids(problem):
        required_vars = [
            selected[slot.slot_id, food_id]
            for slot in problem.meal_slots
            if (slot.slot_id, food_id) in selected
        ]
        if not required_vars:
            return _impossible_result(OptimizationBackend.CP_SAT_V1, "required_food_unavailable")
        model.add(sum(required_vars) >= 1)

    max_repetitions = _max_food_repetitions(problem)
    if max_repetitions is not None:
        for profile in profiles:
            model.add(
                sum(selected[slot.slot_id, profile.food.food_id] for slot in problem.meal_slots)
                <= max_repetitions
            )

    for forbidden in forbidden_selections:
        variables = [selected[key] for key in forbidden if key in selected]
        if variables:
            model.add(sum(variables) <= len(variables) - 1)

    objective_terms = []
    for slot in problem.meal_slots:
        for nutrient_range in slot.nutrient_ranges:
            expression = _nutrient_expression(
                profiles, slot.slot_id, nutrient_range.metric, quantity_steps
            )
            _add_range_constraint(model, expression, nutrient_range)
            deviation = model.new_int_var(0, _range_cap(nutrient_range), f"dev_{slot.slot_id}_{nutrient_range.metric}")
            preferred = _scaled(nutrient_range.preferred)
            model.add(deviation >= expression - preferred)
            model.add(deviation >= preferred - expression)
            objective_terms.append(max(1, round(nutrient_range.weight * 10)) * deviation)

    for nutrient_range in problem.daily_nutrient_ranges:
        expression = sum(
            _nutrient_expression(profiles, slot.slot_id, nutrient_range.metric, quantity_steps)
            for slot in problem.meal_slots
        )
        _add_range_constraint(model, expression, nutrient_range)
        deviation = model.new_int_var(
            0,
            _range_cap(nutrient_range),
            f"daily_dev_{nutrient_range.metric}",
        )
        preferred = _scaled(nutrient_range.preferred)
        model.add(deviation >= expression - preferred)
        model.add(deviation >= preferred - expression)
        objective_terms.append(max(1, round(nutrient_range.weight * 10)) * deviation)

    preferred_ids = {int(value) for value in problem.preferences.get("preferred_food_ids", ())}
    for slot in problem.meal_slots:
        for profile in profiles:
            y = selected[slot.slot_id, profile.food.food_id]
            objective_terms.append(20 * y)
            if profile.food.food_id in preferred_ids:
                objective_terms.append(-10 * y)
            if slot.meal_kind and slot.meal_kind not in profile.meal_affinities:
                objective_terms.append(5 * y)

    model.minimize(sum(objective_terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = problem.time_limit_ms / 1000.0
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = problem.deterministic_seed
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return _impossible_result(
            OptimizationBackend.CP_SAT_V1,
            "cp_sat_infeasible" if status == cp_model.INFEASIBLE else "cp_sat_no_solution",
            solver_status=solver.status_name(status),
        )

    meals = []
    for slot in problem.meal_slots:
        portions = []
        totals = {metric: 0.0 for metric in _nutrient_metrics()}
        for profile in profiles:
            steps = solver.value(quantity_steps[slot.slot_id, profile.food.food_id])
            if steps <= 0:
                continue
            quantity_g = steps * profile.food.bounds.normalized().step_g
            nutrients = profile.food.macros_for_quantity(quantity_g).as_dict()
            for metric in totals:
                totals[metric] += float(nutrients[metric])
            portions.append(
                SelectedPortionV2(
                    slot_id=slot.slot_id,
                    food_id=profile.food.food_id,
                    name=profile.food.name,
                    quantity_g=quantity_g,
                    nutrients=nutrients,
                    functional_roles=profile.functional_roles,
                )
            )
        meals.append(
            MealSolutionV2(
                slot_id=slot.slot_id,
                archetype=slot_archetypes[slot.slot_id].key,
                portions=tuple(portions),
                nutrient_totals=totals,
            )
        )
    return OptimizationPlanResultV2(
        backend=OptimizationBackend.CP_SAT_V1,
        status=OptimizationStatus.OPTIMAL if status == cp_model.OPTIMAL else OptimizationStatus.ACCEPTABLE,
        objective_value=solver.objective_value,
        meals=tuple(meals),
        daily_totals=_sum_meal_totals(meals),
        diagnostics={
            "solver_status": solver.status_name(status),
            "wall_time_seconds": round(solver.wall_time, 4),
            "branches": solver.num_branches,
        },
    )


def _nutrient_expression(profiles, slot_id, metric, quantity_steps):
    return sum(
        _nutrient_per_step(profile, metric) * quantity_steps[slot_id, profile.food.food_id]
        for profile in profiles
    )


def _nutrient_per_step(profile, metric: str) -> int:
    food = profile.food
    per_100g = {
        "kcal": food.kcal_per_100g,
        "protein": food.protein_per_100g,
        "carbs": food.carbs_per_100g,
        "fat": food.fat_per_100g,
    }.get(metric)
    if per_100g is None:
        raise ValueError(f"unsupported_nutrient_metric:{metric}")
    return _scaled(per_100g * food.bounds.normalized().step_g / 100.0)


def _add_range_constraint(model, expression, nutrient_range: NutrientRange) -> None:
    model.add(expression >= _scaled(nutrient_range.minimum))
    model.add(expression <= _scaled(nutrient_range.maximum))


def _scaled(value: float) -> int:
    return round(float(value) * 100)


def _range_cap(nutrient_range: NutrientRange) -> int:
    return max(_scaled(nutrient_range.maximum), _scaled(nutrient_range.preferred), 1)


def _excluded_food_ids(problem: OptimizationProblemV2) -> tuple[int, ...]:
    values = set()
    for constraint in problem.constraints:
        if constraint.severity.lower() != "hard" or constraint.constraint_type != "exclude_food_id":
            continue
        payload = constraint.payload
        candidates = payload.get("food_ids", (payload.get("food_id"),))
        values.update(int(value) for value in candidates if value is not None)
    return tuple(sorted(values))


def _required_food_ids(problem: OptimizationProblemV2) -> tuple[int, ...]:
    values = set()
    for constraint in problem.constraints:
        if constraint.severity.lower() != "hard" or constraint.constraint_type != "require_food_id":
            continue
        payload = constraint.payload
        candidates = payload.get("food_ids", (payload.get("food_id"),))
        values.update(int(value) for value in candidates if value is not None)
    return tuple(sorted(values))


def _max_food_repetitions(problem: OptimizationProblemV2) -> int | None:
    values = []
    for constraint in problem.constraints:
        if constraint.severity.lower() != "hard" or constraint.constraint_type != "max_food_repetitions":
            continue
        if constraint.payload.get("count") is not None:
            values.append(max(0, int(constraint.payload["count"])))
    return min(values) if values else None


def _macro_target(ranges: tuple[NutrientRange, ...]) -> MacroTarget:
    values = {item.metric: item.preferred for item in ranges}
    return MacroTarget(
        kcal=values.get("kcal", 0),
        protein=values.get("protein", 0),
        carbs=values.get("carbs", 0),
        fat=values.get("fat", 0),
    )


def _nutrient_metrics() -> tuple[str, ...]:
    return ("kcal", "protein", "carbs", "fat")


def _sum_meal_totals(meals: list[MealSolutionV2]) -> dict[str, float]:
    return {
        metric: sum(float(meal.nutrient_totals.get(metric, 0)) for meal in meals)
        for metric in _nutrient_metrics()
    }


def _selection_signature(result: OptimizationPlanResultV2) -> tuple[tuple[str, int], ...]:
    return tuple(
        sorted(
            (meal.slot_id, portion.food_id)
            for meal in result.meals
            for portion in meal.portions
        )
    )


def _impossible_result(
    backend: OptimizationBackend,
    reason: str,
    **diagnostics: Any,
) -> OptimizationPlanResultV2:
    return OptimizationPlanResultV2(
        backend=backend,
        status=OptimizationStatus.IMPOSSIBLE,
        objective_value=0,
        diagnostics={"reason": reason, **diagnostics},
    )
