from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nutrition_solver.application.contracts import OptimizationStatus
from nutrition_solver.application.optimizer_v2 import (
    OptimizationBackend,
    OptimizationPlanResultV2,
    solve_optimization_problem,
)
from nutrition_solver.application.problem_v2 import OptimizationProblemV2
from nutrition_solver.application.quality import OptimizationQualityReport, assess_optimization_quality


@dataclass(frozen=True)
class ShadowComparison:
    active_result: OptimizationPlanResultV2
    shadow_result: OptimizationPlanResultV2
    active_quality: OptimizationQualityReport
    shadow_quality: OptimizationQualityReport
    selection_overlap: float
    hard_regression: bool
    regression_reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "active_backend": self.active_result.backend.value,
            "shadow_backend": self.shadow_result.backend.value,
            "active_status": self.active_result.status.value,
            "shadow_status": self.shadow_result.status.value,
            "active_quality": self.active_quality.as_dict(),
            "shadow_quality": self.shadow_quality.as_dict(),
            "selection_overlap": round(self.selection_overlap, 4),
            "hard_regression": self.hard_regression,
            "regression_reasons": list(self.regression_reasons),
        }

    def as_telemetry(self) -> dict[str, Any]:
        return {
            "active_backend": self.active_result.backend.value,
            "shadow_backend": self.shadow_result.backend.value,
            "status_changed": self.active_result.status != self.shadow_result.status,
            "nutritional_score_delta": round(
                self.shadow_quality.nutritional_score - self.active_quality.nutritional_score,
                2,
            ),
            "functional_score_delta": round(
                self.shadow_quality.functional_score - self.active_quality.functional_score,
                2,
            ),
            "selection_overlap": round(self.selection_overlap, 4),
            "hard_regression": self.hard_regression,
            "regression_reasons": list(self.regression_reasons),
        }


def compare_solver_backends(
    problem: OptimizationProblemV2,
    *,
    active_backend: OptimizationBackend | str,
    shadow_backend: OptimizationBackend | str,
) -> ShadowComparison:
    active_result = solve_optimization_problem(problem, backend=active_backend)
    shadow_result = solve_optimization_problem(problem, backend=shadow_backend)
    active_quality = assess_optimization_quality(problem, active_result)
    shadow_quality = assess_optimization_quality(problem, shadow_result)
    active_selection = _selected_foods(active_result)
    shadow_selection = _selected_foods(shadow_result)
    union = active_selection | shadow_selection
    overlap = len(active_selection & shadow_selection) / len(union) if union else 1.0

    reasons = []
    if active_result.status != OptimizationStatus.IMPOSSIBLE and shadow_result.status == OptimizationStatus.IMPOSSIBLE:
        reasons.append("shadow_became_impossible")
    if shadow_quality.nutritional_score + 15 < active_quality.nutritional_score:
        reasons.append("shadow_nutritional_score_regressed")
    if shadow_quality.functional_score + 20 < active_quality.functional_score:
        reasons.append("shadow_functional_score_regressed")

    return ShadowComparison(
        active_result=active_result,
        shadow_result=shadow_result,
        active_quality=active_quality,
        shadow_quality=shadow_quality,
        selection_overlap=overlap,
        hard_regression=bool(reasons),
        regression_reasons=tuple(reasons),
    )


def _selected_foods(result: OptimizationPlanResultV2) -> set[tuple[str, int]]:
    return {
        (meal.slot_id, portion.food_id)
        for meal in result.meals
        for portion in meal.portions
    }
