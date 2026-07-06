"""Persistence boundary for Nutrition Solver.

S6 moves pure domain dataclasses to ``nutrition_solver.domain.models`` but still
defines no database models. The app remains calculation-focused; persisted
Food, Meal, DailyPlan, Program and NutritionProposal entities stay in ``notas``.
"""
