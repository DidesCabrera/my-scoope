from django.test import SimpleTestCase

from notas.application.nutrition_engine.models import MacroTarget, PortionBounds, SolverFood
from notas.application.nutrition_engine.portion_solver import solve_meal_portions


class NutritionEnginePortionSolverV2Tests(SimpleTestCase):
    def test_solver_omits_optional_food_when_it_worsens_target(self):
        result = solve_meal_portions(
            foods=[
                SolverFood(
                    food_id=1,
                    name="Pechuga de pollo",
                    role="protein",
                    protein_per_100g=31,
                    carbs_per_100g=0,
                    fat_per_100g=3,
                    kcal_per_100g=151,
                    bounds=PortionBounds(90, 260, 5),
                    required=True,
                ),
                SolverFood(
                    food_id=2,
                    name="Arroz cocido",
                    role="carb",
                    protein_per_100g=2.5,
                    carbs_per_100g=28,
                    fat_per_100g=0.2,
                    kcal_per_100g=124,
                    bounds=PortionBounds(45, 240, 5),
                    required=True,
                ),
                SolverFood(
                    food_id=3,
                    name="Aceite de oliva",
                    role="fat",
                    protein_per_100g=0,
                    carbs_per_100g=0,
                    fat_per_100g=100,
                    kcal_per_100g=900,
                    bounds=PortionBounds(5, 30, 5),
                    required=False,
                ),
            ],
            target=MacroTarget(kcal=360, protein=35, carbs=48, fat=4),
        )

        used_ids = {portion.food_id for portion in result.portions}

        self.assertIn(1, used_ids)
        self.assertIn(2, used_ids)
        self.assertNotIn(3, used_ids)
        self.assertLess(abs(result.diagnostics.diff_percent["kcal"]), 12)

    def test_solver_includes_optional_food_when_fat_target_requires_it(self):
        result = solve_meal_portions(
            foods=[
                SolverFood(
                    food_id=1,
                    name="Pechuga de pollo",
                    role="protein",
                    protein_per_100g=31,
                    carbs_per_100g=0,
                    fat_per_100g=3,
                    kcal_per_100g=151,
                    bounds=PortionBounds(90, 260, 5),
                    required=True,
                ),
                SolverFood(
                    food_id=2,
                    name="Papa cocida",
                    role="carb",
                    protein_per_100g=2,
                    carbs_per_100g=20,
                    fat_per_100g=0.1,
                    kcal_per_100g=89,
                    bounds=PortionBounds(80, 300, 5),
                    required=True,
                ),
                SolverFood(
                    food_id=3,
                    name="Palta",
                    role="fat",
                    protein_per_100g=2,
                    carbs_per_100g=8.5,
                    fat_per_100g=14.7,
                    kcal_per_100g=174,
                    bounds=PortionBounds(20, 90, 5),
                    required=False,
                ),
            ],
            target=MacroTarget(kcal=520, protein=40, carbs=58, fat=16),
        )

        portions_by_id = {portion.food_id: portion for portion in result.portions}

        self.assertIn(3, portions_by_id)
        self.assertGreaterEqual(portions_by_id[3].quantity_g, 20)
        self.assertLess(abs(result.diagnostics.diff_percent["fat"]), 35)

    def test_solver_reports_macro_notes_for_large_deviations(self):
        result = solve_meal_portions(
            foods=[
                SolverFood(
                    food_id=1,
                    name="Pechuga de pollo",
                    role="protein",
                    protein_per_100g=31,
                    carbs_per_100g=0,
                    fat_per_100g=3,
                    kcal_per_100g=151,
                    bounds=PortionBounds(90, 100, 5),
                    required=True,
                ),
                SolverFood(
                    food_id=2,
                    name="Arroz cocido",
                    role="carb",
                    protein_per_100g=2.5,
                    carbs_per_100g=28,
                    fat_per_100g=0.2,
                    kcal_per_100g=124,
                    bounds=PortionBounds(45, 60, 5),
                    required=True,
                ),
            ],
            target=MacroTarget(kcal=900, protein=80, carbs=120, fat=20),
        )

        joined_notes = " ".join(result.diagnostics.notes)

        self.assertIn("Kcal fuera", joined_notes)
        self.assertIn("Proteína fuera", joined_notes)
