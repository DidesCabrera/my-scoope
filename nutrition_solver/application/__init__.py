"""Application-level pure contracts for the nutrition solver app."""

from .contracts import (
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

__all__ = [
    "DEFAULT_OPTIMIZATION_SCORING_CONFIG",
    "OptimizationDiagnostics",
    "OptimizationInput",
    "OptimizationResult",
    "OptimizationScoringConfig",
    "OptimizationStatus",
    "OptimizationStatusAssessment",
    "SolverConstraint",
    "assess_optimization_status",
    "impossible_optimization_result",
    "infer_optimization_status",
    "optimize_meal_portions",
]
