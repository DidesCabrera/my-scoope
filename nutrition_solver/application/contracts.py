from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


from nutrition_solver.application.portion_solver import (
    PortionSolverConfig,
    PortionSolverError,
    solve_meal_portions,
)

from nutrition_solver.domain.models import (
    MacroTarget,
    PortionSolverDiagnostics,
    PortionSolverResult,
    SolvedFoodPortion,
    SolverFood,
)


class OptimizationStatus(str, Enum):
    """Machine-readable status for nutrition optimization results.

    This status lives above the current portion solver result. It gives future
    UI, AI Assistant tools and Proposal Review flows a stable vocabulary without
    forcing a physical `nutrition_solver` app split yet.
    """

    OPTIMAL = "optimal"
    ACCEPTABLE = "acceptable"
    PARTIAL = "partial"
    IMPOSSIBLE = "impossible"


@dataclass(frozen=True)
class OptimizationScoringConfig:
    """Thresholds used to translate macro deviation into solver status.

    The current portion solver exposes a numeric internal score where lower is
    better. UI, Proposal Review and AI Assistant should not infer quality from
    that opaque score alone. These thresholds define the user-facing status
    vocabulary from macro deviations in a stable, serializable way.
    """

    optimal_tolerance_percent: float = 8.0
    acceptable_tolerance_percent: float = 18.0
    score_direction: str = "lower_is_better"

    def __post_init__(self) -> None:
        optimal = max(0.0, float(self.optimal_tolerance_percent))
        acceptable = max(optimal, float(self.acceptable_tolerance_percent))
        object.__setattr__(self, "optimal_tolerance_percent", optimal)
        object.__setattr__(self, "acceptable_tolerance_percent", acceptable)
        object.__setattr__(self, "score_direction", str(self.score_direction or "lower_is_better"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "optimal_tolerance_percent": round(float(self.optimal_tolerance_percent), 2),
            "acceptable_tolerance_percent": round(float(self.acceptable_tolerance_percent), 2),
            "score_direction": self.score_direction,
        }


DEFAULT_OPTIMIZATION_SCORING_CONFIG = OptimizationScoringConfig()


@dataclass(frozen=True)
class OptimizationStatusAssessment:
    """Human- and machine-readable explanation for an optimization status."""

    status: OptimizationStatus
    reason_code: str
    worst_macro: str | None = None
    worst_deviation_percent: float | None = None
    applied_tolerance_percent: float | None = None
    score_direction: str = "lower_is_better"

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", OptimizationStatus(self.status))
        object.__setattr__(self, "reason_code", str(self.reason_code or "unknown"))
        object.__setattr__(self, "worst_macro", self.worst_macro or None)
        if self.worst_deviation_percent is not None:
            object.__setattr__(self, "worst_deviation_percent", float(self.worst_deviation_percent))
        if self.applied_tolerance_percent is not None:
            object.__setattr__(self, "applied_tolerance_percent", float(self.applied_tolerance_percent))
        object.__setattr__(self, "score_direction", str(self.score_direction or "lower_is_better"))

    @classmethod
    def impossible(cls, *, reason_code: str = "solver_impossible") -> "OptimizationStatusAssessment":
        return cls(
            status=OptimizationStatus.IMPOSSIBLE,
            reason_code=reason_code,
            worst_macro=None,
            worst_deviation_percent=None,
            applied_tolerance_percent=None,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "reason_code": self.reason_code,
            "worst_macro": self.worst_macro,
            "worst_deviation_percent": (
                round(float(self.worst_deviation_percent), 2)
                if self.worst_deviation_percent is not None
                else None
            ),
            "applied_tolerance_percent": (
                round(float(self.applied_tolerance_percent), 2)
                if self.applied_tolerance_percent is not None
                else None
            ),
            "score_direction": self.score_direction,
        }


@dataclass(frozen=True)
class SolverConstraint:
    """Serializable constraint passed to the future nutrition solver boundary."""

    constraint_type: str
    severity: str = "hard"
    payload: Mapping[str, Any] = field(default_factory=dict)
    message: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "constraint_type", str(self.constraint_type).strip())
        object.__setattr__(self, "severity", str(self.severity or "hard").strip() or "hard")
        object.__setattr__(self, "payload", dict(self.payload or {}))
        object.__setattr__(self, "message", str(self.message or ""))

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": self.constraint_type,
            "severity": self.severity,
            "payload": dict(self.payload),
            "message": self.message,
        }


@dataclass(frozen=True)
class OptimizationInput:
    """Optimization-level input contract for the current nutrition engine.

    The contract intentionally accepts pure nutrition-engine models. Adapters
    from `notas.Food` or future apps should convert ORM rows into this shape at
    the boundary; this object must stay free of request, template, session or
    provider-payload dependencies.
    """

    target: MacroTarget
    candidate_foods: tuple[SolverFood, ...]
    meal_slots: tuple[str, ...] = ()
    constraints: tuple[SolverConstraint, ...] = ()
    preferences: Mapping[str, Any] = field(default_factory=dict)
    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_foods", tuple(self.candidate_foods or ()))
        object.__setattr__(self, "meal_slots", tuple(str(slot) for slot in (self.meal_slots or ())))
        object.__setattr__(self, "constraints", tuple(self.constraints or ()))
        object.__setattr__(self, "preferences", dict(self.preferences or {}))
        object.__setattr__(self, "context", dict(self.context or {}))

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": self.target.as_dict(),
            "candidate_foods": [_solver_food_as_dict(food) for food in self.candidate_foods],
            "meal_slots": list(self.meal_slots),
            "constraints": [constraint.as_dict() for constraint in self.constraints],
            "preferences": dict(self.preferences),
            "context": dict(self.context),
        }


@dataclass(frozen=True)
class OptimizationDiagnostics:
    """Stable diagnostics contract shared by solver, UI and AI tools."""

    status: OptimizationStatus
    score: float
    target: MacroTarget
    actual: MacroTarget
    diff: MacroTarget
    diff_percent: Mapping[str, float | None]
    notes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    assessment: OptimizationStatusAssessment | None = None
    scoring_config: OptimizationScoringConfig = DEFAULT_OPTIMIZATION_SCORING_CONFIG

    def __post_init__(self) -> None:
        status = OptimizationStatus(self.status)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "score", float(self.score))
        object.__setattr__(self, "diff_percent", dict(self.diff_percent or {}))
        object.__setattr__(self, "notes", tuple(str(note) for note in (self.notes or ())))
        object.__setattr__(self, "warnings", tuple(str(warning) for warning in (self.warnings or ())))
        object.__setattr__(self, "errors", tuple(str(error) for error in (self.errors or ())))
        object.__setattr__(self, "metadata", dict(self.metadata or {}))
        scoring_config = self.scoring_config or DEFAULT_OPTIMIZATION_SCORING_CONFIG
        object.__setattr__(self, "scoring_config", scoring_config)
        if self.assessment is None:
            assessment = assess_optimization_status(
                self.diff_percent,
                scoring_config=scoring_config,
                override_status=status,
            )
            object.__setattr__(self, "assessment", assessment)
        else:
            object.__setattr__(self, "assessment", self.assessment)

    @classmethod
    def from_portion_solver_diagnostics(
        cls,
        diagnostics: PortionSolverDiagnostics,
        *,
        status: OptimizationStatus | str | None = None,
        warnings: tuple[str, ...] | list[str] = (),
        errors: tuple[str, ...] | list[str] = (),
        metadata: Mapping[str, Any] | None = None,
        scoring_config: OptimizationScoringConfig | None = None,
    ) -> "OptimizationDiagnostics":
        scoring = scoring_config or DEFAULT_OPTIMIZATION_SCORING_CONFIG
        assessment = assess_optimization_status(
            diagnostics.diff_percent,
            scoring_config=scoring,
            override_status=OptimizationStatus(status) if status else None,
        )
        return cls(
            status=assessment.status,
            score=diagnostics.score,
            target=diagnostics.target,
            actual=diagnostics.actual,
            diff=diagnostics.diff,
            diff_percent=diagnostics.diff_percent,
            notes=tuple(diagnostics.notes),
            warnings=tuple(warnings),
            errors=tuple(errors),
            metadata={
                "iterations": diagnostics.iterations,
                **dict(metadata or {}),
            },
            assessment=assessment,
            scoring_config=scoring,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "score": round(float(self.score), 4),
            "score_direction": self.scoring_config.score_direction,
            "target": self.target.as_dict(),
            "actual": self.actual.as_dict(),
            "diff": self.diff.as_dict(),
            "diff_percent": {
                key: round(value, 2) if value is not None else None
                for key, value in self.diff_percent.items()
            },
            "notes": list(self.notes),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "issue_counts": {
                "warnings": len(self.warnings),
                "errors": len(self.errors),
            },
            "assessment": self.assessment.as_dict() if self.assessment else None,
            "scoring_config": self.scoring_config.as_dict(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class OptimizationResult:
    """Optimization-level output contract for solver consumers."""

    status: OptimizationStatus
    score: float
    portions: tuple[SolvedFoodPortion, ...]
    diagnostics: OptimizationDiagnostics

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", OptimizationStatus(self.status))
        object.__setattr__(self, "score", float(self.score))
        object.__setattr__(self, "portions", tuple(self.portions or ()))

    @classmethod
    def from_portion_solver_result(
        cls,
        result: PortionSolverResult,
        *,
        status: OptimizationStatus | str | None = None,
        warnings: tuple[str, ...] | list[str] = (),
        errors: tuple[str, ...] | list[str] = (),
        metadata: Mapping[str, Any] | None = None,
        scoring_config: OptimizationScoringConfig | None = None,
    ) -> "OptimizationResult":
        diagnostics = OptimizationDiagnostics.from_portion_solver_diagnostics(
            result.diagnostics,
            status=status,
            warnings=warnings,
            errors=errors,
            metadata=metadata,
            scoring_config=scoring_config,
        )
        return cls(
            status=diagnostics.status,
            score=diagnostics.score,
            portions=tuple(result.portions),
            diagnostics=diagnostics,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "score": round(float(self.score), 4),
            "portions": [portion.as_dict() for portion in self.portions],
            "diagnostics": self.diagnostics.as_dict(),
        }



def assess_optimization_status(
    diff_percent: Mapping[str, float | None],
    *,
    scoring_config: OptimizationScoringConfig | None = None,
    override_status: OptimizationStatus | str | None = None,
) -> OptimizationStatusAssessment:
    """Build the explicit status assessment used by optimization diagnostics."""
    scoring = scoring_config or DEFAULT_OPTIMIZATION_SCORING_CONFIG

    if override_status == OptimizationStatus.IMPOSSIBLE or str(override_status or "") == OptimizationStatus.IMPOSSIBLE.value:
        return OptimizationStatusAssessment.impossible()

    comparable = {
        key: abs(float(value))
        for key, value in (diff_percent or {}).items()
        if value is not None
    }
    if not comparable:
        status = OptimizationStatus(override_status) if override_status else OptimizationStatus.PARTIAL
        return OptimizationStatusAssessment(
            status=status,
            reason_code="missing_comparable_macro_deviation",
            worst_macro=None,
            worst_deviation_percent=None,
            applied_tolerance_percent=None,
            score_direction=scoring.score_direction,
        )

    worst_macro, worst_deviation = max(comparable.items(), key=lambda item: item[1])
    inferred_status, reason_code, applied_tolerance = _status_from_worst_deviation(
        worst_deviation=worst_deviation,
        scoring_config=scoring,
    )
    status = OptimizationStatus(override_status) if override_status else inferred_status
    return OptimizationStatusAssessment(
        status=status,
        reason_code=reason_code,
        worst_macro=worst_macro,
        worst_deviation_percent=worst_deviation,
        applied_tolerance_percent=applied_tolerance,
        score_direction=scoring.score_direction,
    )


def infer_optimization_status(
    diagnostics: PortionSolverDiagnostics,
    *,
    optimal_tolerance_percent: float = 8.0,
    acceptable_tolerance_percent: float = 18.0,
) -> OptimizationStatus:
    """Infer a coarse optimization status from macro deviation percentages."""
    scoring_config = OptimizationScoringConfig(
        optimal_tolerance_percent=optimal_tolerance_percent,
        acceptable_tolerance_percent=acceptable_tolerance_percent,
    )
    return assess_optimization_status(
        diagnostics.diff_percent,
        scoring_config=scoring_config,
    ).status


def impossible_optimization_result(
    *,
    target: MacroTarget,
    reason: str,
    score: float = 0.0,
    warnings: tuple[str, ...] | list[str] = (),
    metadata: Mapping[str, Any] | None = None,
    scoring_config: OptimizationScoringConfig | None = None,
) -> OptimizationResult:
    """Build a serializable impossible result without raising through UI/tool layers."""
    scoring = scoring_config or DEFAULT_OPTIMIZATION_SCORING_CONFIG
    zero = MacroTarget(kcal=0, protein=0, carbs=0, fat=0)
    diagnostics = OptimizationDiagnostics(
        status=OptimizationStatus.IMPOSSIBLE,
        score=score,
        target=target,
        actual=zero,
        diff=MacroTarget(
            kcal=-target.kcal,
            protein=-target.protein,
            carbs=-target.carbs,
            fat=-target.fat,
        ),
        diff_percent={"kcal": None, "protein": None, "carbs": None, "fat": None},
        warnings=tuple(warnings),
        errors=(str(reason),),
        metadata=dict(metadata or {}),
        assessment=OptimizationStatusAssessment.impossible(reason_code=str(reason)),
        scoring_config=scoring,
    )
    return OptimizationResult(
        status=OptimizationStatus.IMPOSSIBLE,
        score=score,
        portions=(),
        diagnostics=diagnostics,
    )


def _status_from_worst_deviation(
    *,
    worst_deviation: float,
    scoring_config: OptimizationScoringConfig,
) -> tuple[OptimizationStatus, str, float]:
    if worst_deviation <= scoring_config.optimal_tolerance_percent:
        return (
            OptimizationStatus.OPTIMAL,
            "within_optimal_tolerance",
            scoring_config.optimal_tolerance_percent,
        )
    if worst_deviation <= scoring_config.acceptable_tolerance_percent:
        return (
            OptimizationStatus.ACCEPTABLE,
            "within_acceptable_tolerance",
            scoring_config.acceptable_tolerance_percent,
        )
    return (
        OptimizationStatus.PARTIAL,
        "outside_acceptable_tolerance",
        scoring_config.acceptable_tolerance_percent,
    )



def _solver_food_as_dict(food: SolverFood) -> dict[str, Any]:
    bounds = food.bounds.normalized()
    return {
        "food_id": food.food_id,
        "name": food.name,
        "role": food.role,
        "protein_per_100g": round(float(food.protein_per_100g), 2),
        "carbs_per_100g": round(float(food.carbs_per_100g), 2),
        "fat_per_100g": round(float(food.fat_per_100g), 2),
        "kcal_per_100g": round(float(food.kcal_per_100g), 2),
        "bounds": {
            "minimum_g": round(float(bounds.minimum_g), 2),
            "maximum_g": round(float(bounds.maximum_g), 2),
            "step_g": round(float(bounds.step_g), 2),
        },
        "required": bool(food.required),
    }


def optimize_meal_portions(
    optimization_input: OptimizationInput,
    *,
    config: PortionSolverConfig | None = None,
    scoring_config: OptimizationScoringConfig | None = None,
) -> OptimizationResult:
    """Resolve one meal through the extracted nutrition-solver boundary.

    The optimization input/result/status contracts and the deterministic portion
    solver now live inside ``nutrition_solver``. Callers from ``notas`` should
    keep using the legacy bridge during the migration window, but new solver
    consumers can depend on this function directly.
    """
    candidate_foods = tuple(optimization_input.candidate_foods)
    warnings = _build_input_warnings(optimization_input)
    metadata = {
        "candidate_count": len(candidate_foods),
        "constraint_count": len(optimization_input.constraints),
        "meal_slots": list(optimization_input.meal_slots),
    }

    if not candidate_foods:
        return impossible_optimization_result(
            target=optimization_input.target,
            reason="solver_requires_candidate_foods",
            metadata=metadata,
            warnings=warnings,
            scoring_config=scoring_config,
        )

    try:
        portion_result = solve_meal_portions(
            foods=list(candidate_foods),
            target=optimization_input.target,
            config=config,
        )
    except PortionSolverError as exc:
        return impossible_optimization_result(
            target=optimization_input.target,
            reason=str(exc),
            metadata=metadata,
            warnings=warnings,
            scoring_config=scoring_config,
        )

    return OptimizationResult.from_portion_solver_result(
        portion_result,
        warnings=warnings,
        metadata=metadata,
        scoring_config=scoring_config,
    )


def _build_input_warnings(optimization_input: OptimizationInput) -> tuple[str, ...]:
    warnings: list[str] = []
    if not optimization_input.meal_slots:
        warnings.append("optimization_input_missing_meal_slots")

    soft_constraints = [
        constraint
        for constraint in optimization_input.constraints
        if constraint.severity.lower() == "soft"
    ]
    if soft_constraints:
        warnings.append("optimization_input_contains_soft_constraints")

    return tuple(warnings)
