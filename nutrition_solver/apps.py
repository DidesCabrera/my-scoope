from django.apps import AppConfig


class NutritionSolverConfig(AppConfig):
    """Django app boundary for deterministic nutrition optimization."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "nutrition_solver"
    verbose_name = "Nutrition Solver"
