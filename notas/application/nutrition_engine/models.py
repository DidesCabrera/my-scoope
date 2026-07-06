"""Compatibility imports for pure nutrition-solver domain models.

Patch S6 moves the pure model dataclasses to ``nutrition_solver.domain.models``.
This module intentionally remains as a temporary bridge so current imports from
``notas.application.nutrition_engine.models`` keep working while the solver is
extracted progressively.
"""

from nutrition_solver.domain.models import (
    MacroTarget,
    PortionBounds,
    PortionSolverDiagnostics,
    PortionSolverResult,
    SolvedFoodPortion,
    SolverFood,
)

__all__ = [
    "MacroTarget",
    "PortionBounds",
    "PortionSolverDiagnostics",
    "PortionSolverResult",
    "SolvedFoodPortion",
    "SolverFood",
]
