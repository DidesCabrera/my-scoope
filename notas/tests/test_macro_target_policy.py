from django.test import SimpleTestCase

from notas.application.nutrition_engine.macro_target_policy import (
    resolve_daily_macro_targets,
)


class MacroTargetPolicyTests(SimpleTestCase):
    def test_keeps_ppk_stable_and_moves_carbohydrates_with_energy(self):
        deficit = resolve_daily_macro_targets(
            total_kcal=2000,
            weight_kg=80,
            default_protein_per_kg=1.8,
        )
        surplus = resolve_daily_macro_targets(
            total_kcal=2600,
            weight_kg=80,
            default_protein_per_kg=1.8,
        )

        self.assertEqual(deficit.protein, surplus.protein)
        self.assertAlmostEqual(deficit.protein_per_kg, deficit.protein / 80)
        self.assertGreater(surplus.carbs, deficit.carbs)
        self.assertLessEqual(deficit.distribution["fat"], 35)
        self.assertLessEqual(surplus.distribution["fat"], 35)

    def test_accepts_supported_explicit_distributions(self):
        for distribution in (
            {"protein": 30, "carbs": 45, "fat": 25},
            {"protein": 30, "carbs": 50, "fat": 20},
            {"protein": 25, "carbs": 55, "fat": 20},
        ):
            with self.subTest(distribution=distribution):
                result = resolve_daily_macro_targets(
                    total_kcal=2400,
                    weight_kg=80,
                    default_protein_per_kg=1.8,
                    macro_distribution=distribution,
                )
                self.assertEqual(result.distribution, distribution)

    def test_rejects_incoherent_ppk_and_distribution(self):
        with self.assertRaisesMessage(
            ValueError,
            "nutrition_target_ppk_distribution_conflict",
        ):
            resolve_daily_macro_targets(
                total_kcal=1600,
                weight_kg=80,
                default_protein_per_kg=1.8,
                protein_per_kg_target=2.0,
                macro_distribution={"protein": 25, "carbs": 55, "fat": 20},
            )

    def test_rejects_ppk_outside_supported_range_and_excessive_fat(self):
        with self.assertRaisesMessage(ValueError, "nutrition_target_ppk_out_of_supported_range"):
            resolve_daily_macro_targets(
                total_kcal=2200,
                weight_kg=80,
                default_protein_per_kg=1.8,
                protein_per_kg_target=2.8,
            )
        with self.assertRaisesMessage(
            ValueError,
            "nutrition_target_distribution_fat_out_of_supported_range",
        ):
            resolve_daily_macro_targets(
                total_kcal=2200,
                weight_kg=80,
                default_protein_per_kg=1.8,
                macro_distribution={"protein": 25, "carbs": 35, "fat": 40},
            )

    def test_rejects_distribution_that_implies_incoherent_ppk_for_weight(self):
        with self.assertRaisesMessage(
            ValueError,
            "nutrition_target_distribution_ppk_out_of_supported_range",
        ):
            resolve_daily_macro_targets(
                total_kcal=1600,
                weight_kg=100,
                default_protein_per_kg=1.8,
                macro_distribution={"protein": 10, "carbs": 65, "fat": 25},
            )

    def test_marks_supported_extreme_as_outside_preferred_range(self):
        result = resolve_daily_macro_targets(
            total_kcal=2400,
            weight_kg=80,
            default_protein_per_kg=1.8,
            protein_per_kg_target=1.2,
        )

        self.assertEqual(result.protein_per_kg, 1.1875)
        self.assertIn("fuera del rango preferente", result.notes[1])
