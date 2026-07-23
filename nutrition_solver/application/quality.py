from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nutrition_solver.application.contracts import OptimizationStatus
from nutrition_solver.application.optimizer_v2 import OptimizationPlanResultV2
from nutrition_solver.application.problem_v2 import OptimizationProblemV2


@dataclass(frozen=True)
class OptimizationQualityReport:
    nutritional_score: float
    functional_score: float
    hard_constraints_satisfied: bool
    explanations: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "nutritional_score": round(self.nutritional_score, 2),
            "functional_score": round(self.functional_score, 2),
            "hard_constraints_satisfied": self.hard_constraints_satisfied,
            "explanations": list(self.explanations),
            "warnings": list(self.warnings),
        }


def assess_optimization_quality(
    problem: OptimizationProblemV2,
    result: OptimizationPlanResultV2,
) -> OptimizationQualityReport:
    if result.status == OptimizationStatus.IMPOSSIBLE:
        return OptimizationQualityReport(
            nutritional_score=0,
            functional_score=0,
            hard_constraints_satisfied=False,
            explanations=("No feasible result satisfied every hard constraint.",),
            warnings=(str(result.diagnostics.get("reason", "solver_impossible")),),
        )

    deviations = []
    explanations = []
    warnings = []
    meal_by_slot = {meal.slot_id: meal for meal in result.meals}
    slot_by_id = {slot.slot_id: slot for slot in problem.meal_slots}

    for slot_id, slot in slot_by_id.items():
        meal = meal_by_slot.get(slot_id)
        if meal is None:
            warnings.append(f"missing_meal_solution:{slot_id}")
            continue
        for nutrient_range in slot.nutrient_ranges:
            actual = float(meal.nutrient_totals.get(nutrient_range.metric, 0))
            if nutrient_range.preferred > 0:
                deviations.append(abs(actual - nutrient_range.preferred) / nutrient_range.preferred * 100)

    for nutrient_range in problem.daily_nutrient_ranges:
        actual = float(result.daily_totals.get(nutrient_range.metric, 0))
        if nutrient_range.preferred > 0:
            deviations.append(abs(actual - nutrient_range.preferred) / nutrient_range.preferred * 100)

    nutritional_score = max(0.0, 100.0 - (sum(deviations) / len(deviations) if deviations else 0.0))
    explanations.append(f"Average preferred-range proximity: {nutritional_score:.1f}/100.")

    covered_groups = 0
    total_groups = 0
    valid_component_counts = 0
    for meal in result.meals:
        slot = slot_by_id[meal.slot_id]
        archetype = next(
            (item for item in slot.allowed_archetypes if item.key == meal.archetype),
            slot.allowed_archetypes[0],
        )
        selected_roles = {
            role for portion in meal.portions for role in portion.functional_roles
        }
        total_groups += len(archetype.required_role_groups)
        covered_groups += sum(
            1 for group in archetype.required_role_groups if selected_roles.intersection(group)
        )
        if archetype.minimum_components <= len(meal.portions) <= archetype.maximum_components:
            valid_component_counts += 1

    role_score = 100.0 if total_groups == 0 else covered_groups / total_groups * 100
    component_score = 100.0 if not result.meals else valid_component_counts / len(result.meals) * 100
    functional_score = role_score * 0.8 + component_score * 0.2
    explanations.append(f"Meal-grammar coverage: {functional_score:.1f}/100.")

    missing_capability_profiles = sum(1 for profile in problem.food_profiles if not profile.functional_roles)
    if missing_capability_profiles:
        warnings.append(f"profiles_missing_functional_roles:{missing_capability_profiles}")

    return OptimizationQualityReport(
        nutritional_score=nutritional_score,
        functional_score=functional_score,
        hard_constraints_satisfied=True,
        explanations=tuple(explanations),
        warnings=tuple(warnings),
    )
