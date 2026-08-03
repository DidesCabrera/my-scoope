from django.test import SimpleTestCase

from nutrition_solver.domain.models import MacroTarget
from nutrition_solver.application.validators import (
    STATUS_ERROR,
    STATUS_OK,
    STATUS_WARNING,
    PortionValidationInput,
    validate_generated_dailyplan,
)


class NutritionEngineStrictValidatorTests(SimpleTestCase):
    def test_accepts_plan_inside_strict_tolerance_and_constraints(self):
        result = validate_generated_dailyplan(
            target=MacroTarget(kcal=2200, protein=160, carbs=250, fat=70),
            actual=MacroTarget(kcal=2180, protein=158, carbs=248, fat=71),
            expected_meals_count=4,
            actual_meals_count=4,
            excluded_terms=["pescado"],
            portions=[
                PortionValidationInput(
                    food_id=1,
                    food_name="Pechuga de pollo",
                    quantity_g=170,
                    role="protein",
                    minimum_g=90,
                    maximum_g=260,
                ),
                PortionValidationInput(
                    food_id=2,
                    food_name="Arroz cocido",
                    quantity_g=160,
                    role="carb",
                    minimum_g=45,
                    maximum_g=240,
                ),
            ],
        )

        self.assertEqual(result.status, STATUS_OK)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.issues, [])
        self.assertEqual(result.comparison["kcal"]["status"], STATUS_OK)

    def test_classifies_macro_deviation_as_warning_or_error(self):
        warning_result = validate_generated_dailyplan(
            target=MacroTarget(kcal=2200, protein=160, carbs=250, fat=70),
            actual=MacroTarget(kcal=2080, protein=143, carbs=240, fat=68),
        )
        error_result = validate_generated_dailyplan(
            target=MacroTarget(kcal=2200, protein=160, carbs=250, fat=70),
            actual=MacroTarget(kcal=1800, protein=110, carbs=190, fat=48),
        )

        self.assertEqual(warning_result.status, STATUS_WARNING)
        self.assertFalse(warning_result.has_errors)
        self.assertIn("protein_outside_warning_tolerance", {issue.code for issue in warning_result.issues})

        self.assertEqual(error_result.status, STATUS_ERROR)
        self.assertTrue(error_result.has_errors)
        self.assertIn("kcal_outside_error_tolerance", {issue.code for issue in error_result.issues})

    def test_flags_hard_constraint_violations(self):
        result = validate_generated_dailyplan(
            target=MacroTarget(kcal=2000, protein=150, carbs=220, fat=60),
            actual=MacroTarget(kcal=1990, protein=149, carbs=218, fat=61),
            expected_meals_count=4,
            actual_meals_count=3,
            excluded_terms=["arroz"],
            portions=[
                PortionValidationInput(
                    food_id=10,
                    food_name="Arroz cocido",
                    quantity_g=150,
                    role="carb",
                    minimum_g=45,
                    maximum_g=240,
                ),
                PortionValidationInput(
                    food_id=11,
                    food_name="Aceite de oliva",
                    quantity_g=130,
                    role="fat",
                    minimum_g=5,
                    maximum_g=60,
                ),
            ],
        )

        issue_codes = {issue.code for issue in result.issues}

        self.assertEqual(result.status, STATUS_ERROR)
        self.assertIn("meal_count_mismatch", issue_codes)
        self.assertIn("excluded_food_used", issue_codes)
        self.assertIn("portion_above_maximum", issue_codes)
        self.assertFalse(result.is_valid)
        self.assertIn("issues", result.as_dict())
