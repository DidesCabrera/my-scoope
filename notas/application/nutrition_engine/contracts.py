"""Compatibility bridge for extracted nutrition optimization contracts.

Patch S7 moves the optimization wrapper and deterministic solver dependency to
``nutrition_solver``. This module keeps legacy imports stable while ``notas``
callers migrate progressively.
"""

from nutrition_solver.application.contracts import (
    DEFAULT_OPTIMIZATION_SCORING_CONFIG,
    OptimizationDiagnostics,
    OptimizationInput,
    OptimizationResult,
    OptimizationScoringConfig,
    OptimizationStatus,
    OptimizationStatusAssessment,
    SolverConstraint,
    assess_optimization_status,
    impossible_optimization_result,
    infer_optimization_status,
    optimize_meal_portions,
)
from nutrition_solver.application.portion_solver import (
    PortionSolverConfig,
    PortionSolverError,
    solve_meal_portions,
)

__all__ = [
    "DEFAULT_OPTIMIZATION_SCORING_CONFIG",
    "OptimizationDiagnostics",
    "OptimizationInput",
    "OptimizationResult",
    "OptimizationScoringConfig",
    "OptimizationStatus",
    "OptimizationStatusAssessment",
    "PortionSolverConfig",
    "PortionSolverError",
    "SolverConstraint",
    "assess_optimization_status",
    "impossible_optimization_result",
    "infer_optimization_status",
    "optimize_meal_portions",
    "solve_meal_portions",
]
