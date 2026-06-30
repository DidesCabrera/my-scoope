from django.test import SimpleTestCase

from notas.application.nutrition_engine.target_estimator import (
    TargetEstimationProfile,
    estimate_bmr_mifflin_st_jeor,
    estimate_daily_targets,
    estimate_energy_expenditure,
    resolve_energy_adjustment,
)


class TargetEstimatorTests(SimpleTestCase):
    def test_estimates_fat_loss_target_from_bmr_tdee_and_moderate_deficit(self):
        profile = TargetEstimationProfile(
            goal="fat_loss",
            weight_kg=80,
            height_cm=175,
            age_years=30,
            sex="male",
            activity_level="moderate",
        )

        target_plan = estimate_daily_targets(profile)

        self.assertAlmostEqual(target_plan.estimated_bmr, 1748.75, places=2)
        self.assertAlmostEqual(target_plan.estimated_tdee, 2710.56, places=2)
        self.assertEqual(target_plan.energy_adjustment, "deficit_moderate")
        self.assertEqual(target_plan.energy_adjustment_factor, -0.15)
        self.assertEqual(target_plan.total_kcal, 2300)
        self.assertEqual(target_plan.protein, 145)
        self.assertLess(target_plan.total_kcal, target_plan.estimated_tdee)
        self.assertTrue(target_plan.estimated_targets["total_kcal"])
        self.assertEqual(target_plan.estimation_method, "mifflin_st_jeor_tdee_adjusted")

    def test_explicit_targets_override_estimates_but_keep_expenditure_metadata(self):
        profile = TargetEstimationProfile(
            goal="fat_loss",
            weight_kg=80,
            height_cm=175,
            age_years=30,
            sex="male",
            activity_level="moderate",
            calorie_target=1900,
            protein_target=160,
            carb_target=180,
            fat_target=55,
        )

        target_plan = estimate_daily_targets(profile)

        self.assertEqual(target_plan.total_kcal, 1900)
        self.assertEqual(target_plan.protein, 160)
        self.assertEqual(target_plan.carbs, 180)
        self.assertEqual(target_plan.fat, 55)
        self.assertTrue(target_plan.explicit_targets["total_kcal"])
        self.assertFalse(target_plan.estimated_targets["protein"])
        self.assertGreater(target_plan.estimated_tdee, target_plan.total_kcal)
        self.assertIn("energy_expenditure", target_plan.as_targets_dict())

    def test_falls_back_when_body_inputs_are_incomplete(self):
        target_plan = estimate_daily_targets(
            TargetEstimationProfile(goal="healthy_eating")
        )

        self.assertEqual(target_plan.total_kcal, 2200)
        self.assertIsNone(target_plan.estimated_bmr)
        self.assertIsNone(target_plan.estimated_tdee)
        self.assertEqual(target_plan.estimation_method, "default_target_without_full_expenditure_inputs")
        self.assertTrue(any("fallback" in note.lower() for note in target_plan.notes))

    def test_energy_adjustment_defaults_by_goal_and_can_be_overridden(self):
        self.assertEqual(
            resolve_energy_adjustment(goal="fat_loss"),
            "deficit_moderate",
        )
        self.assertEqual(
            resolve_energy_adjustment(goal="muscle_gain"),
            "surplus_mild",
        )
        self.assertEqual(
            resolve_energy_adjustment(goal="fat_loss", requested_adjustment="deficit_large"),
            "deficit_large",
        )

    def test_energy_expenditure_reports_partial_estimate_without_activity(self):
        profile = TargetEstimationProfile(
            weight_kg=70,
            height_cm=165,
            age_years=28,
            sex="female",
        )

        expenditure = estimate_energy_expenditure(profile=profile)

        self.assertAlmostEqual(expenditure.bmr, 1430.25, places=2)
        self.assertIsNone(expenditure.tdee)
        self.assertEqual(expenditure.method, "mifflin_st_jeor_without_activity")
        self.assertIn("falta nivel de actividad", expenditure.notes[0].lower())

    def test_bmr_formula_is_publicly_available_for_engine_callers(self):
        self.assertAlmostEqual(
            estimate_bmr_mifflin_st_jeor(
                weight_kg=80,
                height_cm=175,
                age_years=30,
                sex="male",
            ),
            1748.75,
            places=2,
        )
