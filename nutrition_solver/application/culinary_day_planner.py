"""Culinary-first meal and day planning over validated meal variants.

The planner never invents an unrestricted bag of foods.  It selects one persisted
culinary variant for each meal slot and only optimizes the quantities already
allowed by that variant, including component bounds and culinary ratios.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import ceil, floor
from typing import Mapping, Sequence

from nutrition_solver.application.culinary_planner import (
    CulinaryCandidate,
    CulinaryPlanningError,
)

METRICS = ("kcal", "protein", "carbs", "fat")


@dataclass(frozen=True)
class CulinaryDaySolution:
    meals: tuple[dict, ...]
    totals: dict[str, float]
    objective_value: float
    solver_status: str

    @property
    def selection_signature(self) -> tuple[tuple[int, int], ...]:
        return tuple((int(meal["slot"]), int(meal["variant_id"])) for meal in self.meals)

    def as_dict(self) -> dict:
        return {
            "meals": [dict(meal) for meal in self.meals],
            "totals": dict(self.totals),
            "objective_value": self.objective_value,
            "solver_status": self.solver_status,
            "selection_signature": [list(item) for item in self.selection_signature],
        }


def solve_culinary_day_alternatives(
    *,
    targets: Mapping[str, float],
    slots: Sequence[Mapping[str, object]],
    candidates: Sequence[CulinaryCandidate],
    count: int = 3,
    time_limit_seconds: float = 1.5,
    candidate_width_per_family: int = 4,
) -> tuple[CulinaryDaySolution, ...]:
    """Return distinct, deterministic meal-variant selections for one day."""

    requested = max(1, min(int(count), 10))
    forbidden: list[tuple[tuple[int, int], ...]] = []
    alternatives = []
    for _index in range(requested):
        try:
            solution = _solve_culinary_day(
                targets=targets,
                slots=slots,
                candidates=candidates,
                forbidden=tuple(forbidden),
                time_limit_seconds=time_limit_seconds,
                candidate_width_per_family=candidate_width_per_family,
            )
        except CulinaryPlanningError as exc:
            if alternatives and exc.code == "culinary_day_infeasible":
                break
            raise
        alternatives.append(solution)
        forbidden.append(solution.selection_signature)
    return tuple(alternatives)


def solve_culinary_meal(
    *,
    target: Mapping[str, float],
    meal_kind: str,
    candidates: Sequence[CulinaryCandidate],
    time_limit_seconds: float = 1.5,
) -> CulinaryDaySolution:
    return solve_culinary_day_alternatives(
        targets=target,
        slots=({"kind": meal_kind, "allocation": 1.0, "label": meal_kind},),
        candidates=candidates,
        count=1,
        time_limit_seconds=time_limit_seconds,
    )[0]


def _bounded_candidates(candidates, meal_kind, width):
    families = defaultdict(list)
    for candidate in candidates:
        if meal_kind in candidate.meal_kinds:
            families[candidate.family].append(candidate)
    bounded = []
    for family in sorted(families):
        family_candidates = sorted(families[family], key=lambda item: item.variant_id)
        limit = min(len(family_candidates), max(1, int(width)))
        # Sample the complete family deterministically instead of taking only
        # adjacent Cartesian variants that often differ by dessert alone.
        indexes = {floor(index * len(family_candidates) / limit) for index in range(limit)}
        bounded.extend(family_candidates[index] for index in sorted(indexes))
    return tuple(bounded)


def _solve_culinary_day(
    *,
    targets,
    slots,
    candidates,
    forbidden,
    time_limit_seconds,
    candidate_width_per_family,
):
    from ortools.sat.python import cp_model

    clean_targets = {metric: float(targets[metric]) for metric in METRICS}
    if any(value <= 0 for value in clean_targets.values()):
        raise CulinaryPlanningError("culinary_day_targets_invalid")
    if not slots:
        raise CulinaryPlanningError("culinary_day_slots_required")

    model = cp_model.CpModel()
    selected, quantities, options = {}, {}, {}
    metric_terms = {metric: [] for metric in METRICS}
    objective_terms = []
    family_uses = defaultdict(list)

    for slot_index, slot in enumerate(slots):
        kind = str(slot.get("kind") or "").strip().lower()
        available = _bounded_candidates(candidates, kind, candidate_width_per_family)
        if not available:
            raise CulinaryPlanningError("culinary_catalog_slot_unavailable", slot=kind)
        slot_selected = []
        slot_kcal_terms = []
        for candidate in available:
            key = (slot_index, candidate.variant_id)
            y = model.new_bool_var(f"variant_{slot_index}_{candidate.variant_id}")
            selected[key], options[key] = y, candidate
            slot_selected.append(y)
            family_uses[candidate.family].append(y)
            component_vars = {}
            for ingredient_index, ingredient in enumerate(candidate.ingredients):
                maximum_steps = floor(ingredient.maximum_g / ingredient.step_g)
                minimum_steps = ceil(ingredient.minimum_g / ingredient.step_g)
                q = model.new_int_var(0, maximum_steps, f"portion_{slot_index}_{candidate.variant_id}_{ingredient_index}")
                model.add(q >= minimum_steps * y)
                model.add(q <= maximum_steps * y)
                quantities[key, ingredient_index] = q
                component_vars[ingredient.component] = (q, ingredient.step_g)
                for metric in METRICS:
                    coefficient = round(getattr(ingredient, metric) * ingredient.step_g * 10)
                    term = coefficient * q
                    metric_terms[metric].append(term)
                    if metric == "kcal":
                        slot_kcal_terms.append(term)
            for ratio in candidate.ratios:
                left, left_step = component_vars[ratio["left"]]
                right, right_step = component_vars[ratio["right"]]
                model.add(round(left_step * 1000) * left >= round(ratio["minimum"] * right_step * 1000) * right)
                model.add(round(left_step * 1000) * left <= round(ratio["maximum"] * right_step * 1000) * right)
        model.add(sum(slot_selected) == 1)
        allocation = float(slot.get("allocation") or 0)
        slot_target = round(clean_targets["kcal"] * allocation * 1000)
        model.add(sum(slot_kcal_terms) >= ceil(slot_target * 0.65))
        model.add(sum(slot_kcal_terms) <= floor(slot_target * 1.35))
        deviation = model.new_int_var(0, 10_000_000, f"slot_kcal_deviation_{slot_index}")
        model.add_abs_equality(deviation, sum(slot_kcal_terms) - slot_target)
        objective_terms.append(max(1, round(1_000_000 / slot_target)) * deviation)

    # Do not repeat the exact same prepared variant twice in one day.
    variant_uses = defaultdict(list)
    for (slot_index, variant_id), variable in selected.items():
        variant_uses[variant_id].append(variable)
    for uses in variant_uses.values():
        model.add(sum(uses) <= 1)

    for signature in forbidden:
        variables = [selected[item] for item in signature if item in selected]
        if variables:
            model.add(sum(variables) <= len(variables) - 1)

    tolerances = {
        "kcal": (0.88, 1.12, 4),
        "protein": (0.75, 1.25, 4),
        "carbs": (0.70, 1.30, 2),
        "fat": (0.65, 1.35, 2),
    }
    for metric, (minimum, maximum, weight) in tolerances.items():
        expression = sum(metric_terms[metric])
        target = round(clean_targets[metric] * 1000)
        model.add(expression >= ceil(target * minimum))
        model.add(expression <= floor(target * maximum))
        deviation = model.new_int_var(0, 10_000_000, f"daily_{metric}_deviation")
        model.add_abs_equality(deviation, expression - target)
        objective_terms.append(max(1, round(weight * 1_000_000 / target)) * deviation)

    # Prefer fewer culinary families repeated across slots without making a
    # legitimate breakfast/snack reuse impossible.
    for family, uses in family_uses.items():
        if len(uses) <= 1:
            continue
        repeated = model.new_int_var(0, len(uses), f"family_repeat_{family}")
        model.add(repeated >= sum(uses) - 1)
        objective_terms.append(2_000 * repeated)

    model.minimize(sum(objective_terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = min(max(float(time_limit_seconds), 0.1), 10)
    solver.parameters.num_search_workers = 1
    # The model has sparse conditional portion domains; disabling full presolve
    # avoids spending the complete interactive budget enumerating them.
    solver.parameters.cp_model_presolve = False
    solver.parameters.random_seed = 0
    status = solver.solve(model)
    if status not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        if status == cp_model.INFEASIBLE:
            code = "culinary_day_infeasible"
        elif status == cp_model.MODEL_INVALID:
            code = "culinary_day_model_invalid"
        else:
            code = "culinary_day_search_timeout"
        raise CulinaryPlanningError(
            code,
            solver_status=solver.status_name(status),
            wall_seconds=solver.wall_time,
        )

    meals = []
    totals = dict.fromkeys(METRICS, 0.0)
    for key, y in selected.items():
        if not solver.value(y):
            continue
        slot_index, _variant_id = key
        candidate = options[key]
        foods, components = [], []
        meal_totals = dict.fromkeys(METRICS, 0.0)
        for ingredient_index, ingredient in enumerate(candidate.ingredients):
            quantity = solver.value(quantities[key, ingredient_index]) * ingredient.step_g
            foods.append({"food_id": ingredient.food_id, "quantity": quantity, "unit": ingredient.portion_unit})
            components.append({
                "component": ingredient.component,
                "course": getattr(ingredient, "course", "main"),
                "group": ingredient.group,
                "food_id": ingredient.food_id,
            })
            for metric in METRICS:
                value = getattr(ingredient, metric) * quantity / 100
                meal_totals[metric] += value
                totals[metric] += value
        meals.append({
            "slot": slot_index,
            "variant_id": candidate.variant_id,
            "family": candidate.family,
            "name": candidate.name,
            "preparation": candidate.preparation,
            "foods": foods,
            "components": components,
            "totals": {key: round(value, 2) for key, value in meal_totals.items()},
            "evidence_digest": candidate.evidence_digest,
            "validation_level": candidate.validation_level,
        })
    return CulinaryDaySolution(
        meals=tuple(sorted(meals, key=lambda item: item["slot"])),
        totals={key: round(value, 2) for key, value in totals.items()},
        objective_value=float(solver.objective_value),
        solver_status=solver.status_name(status),
    )
