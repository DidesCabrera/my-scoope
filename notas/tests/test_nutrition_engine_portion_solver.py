from django.test import SimpleTestCase

from nutrition_solver.application.portion_solver import solve_meal_portions
from nutrition_solver.application.validators import compare_macro_targets
from nutrition_solver.domain.models import (
    MacroTarget,
    PortionBounds,
    SolverFood,
)


class PortionSolverTests(SimpleTestCase):
    def test_solver_gets_close_to_meal_targets_with_human_portions(self):
        foods = [
            SolverFood(
                food_id=1,
                name="Pechuga de pollo",
                role="protein",
                protein_per_100g=31,
                carbs_per_100g=0,
                fat_per_100g=3.6,
                kcal_per_100g=156,
                bounds=PortionBounds(90, 260, 5),
            ),
            SolverFood(
                food_id=2,
                name="Arroz cocido",
                role="carb",
                protein_per_100g=2.7,
                carbs_per_100g=28,
                fat_per_100g=0.3,
                kcal_per_100g=125.5,
                bounds=PortionBounds(45, 240, 5),
            ),
            SolverFood(
                food_id=3,
                name="Palta",
                role="fat",
                protein_per_100g=2,
                carbs_per_100g=8.5,
                fat_per_100g=14.7,
                kcal_per_100g=174.3,
                bounds=PortionBounds(5, 60, 5),
                required=False,
            ),
            SolverFood(
                food_id=4,
                name="Tomate",
                role="vegetable",
                protein_per_100g=0.9,
                carbs_per_100g=3.9,
                fat_per_100g=0.2,
                kcal_per_100g=21,
                bounds=PortionBounds(50, 180, 5),
                required=False,
            ),
        ]
        result = solve_meal_portions(
            foods=foods,
            target=MacroTarget(kcal=620, protein=48, carbs=72, fat=17),
        )

        quantities = {portion.role: portion.quantity_g for portion in result.portions}

        self.assertGreaterEqual(quantities["protein"], 90)
        self.assertLessEqual(quantities["protein"], 260)
        self.assertGreaterEqual(quantities["carb"], 45)
        self.assertLessEqual(quantities["carb"], 240)
        self.assertLess(abs(result.diagnostics.diff_percent["kcal"]), 16)
        self.assertLess(abs(result.diagnostics.diff_percent["protein"]), 18)

    def test_validator_flags_macro_comparison(self):
        validation = compare_macro_targets(
            target=MacroTarget(kcal=2200, protein=160, carbs=240, fat=65),
            actual=MacroTarget(kcal=2188, protein=158, carbs=238, fat=66),
        )

        self.assertTrue(validation.is_within_initial_tolerance)
        self.assertEqual(validation.comparison["kcal"]["target"], 2200)
        self.assertIn("tolerancia", validation.notes[0])
