"""Pure domain contracts for the nutrition solver app."""

from .models import (
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
