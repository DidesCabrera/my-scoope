"""Compatibility bridge for the extracted portion solver.

Patch S7 moves the deterministic portion solver implementation to
``nutrition_solver.application.portion_solver``. This module remains so legacy
imports from ``notas.application.nutrition_engine.portion_solver`` continue to
work while callers migrate progressively.
"""

from nutrition_solver.application.portion_solver import (
    DEFAULT_PORTION_SOLVER_CONFIG,
    PortionSolverConfig,
    PortionSolverError,
    solve_meal_portions,
)

__all__ = [
    "DEFAULT_PORTION_SOLVER_CONFIG",
    "PortionSolverConfig",
    "PortionSolverError",
    "solve_meal_portions",
]
