from django.test import SimpleTestCase

from notas.domain.services.nutrition import macro_kcal_distribution


class MacroKcalDistributionTests(SimpleTestCase):
    def test_distribution_normalizes_macro_calories_to_one_hundred_percent(self):
        distribution = macro_kcal_distribution(80, 80, 90)

        self.assertAlmostEqual(distribution["protein"], 32.0)
        self.assertAlmostEqual(distribution["carbs"], 32.0)
        self.assertAlmostEqual(distribution["fat"], 36.0)
        self.assertAlmostEqual(sum(distribution.values()), 100.0)

    def test_distribution_returns_zeroes_for_an_energy_free_entity(self):
        self.assertEqual(
            macro_kcal_distribution(0, 0, 0),
            {"protein": 0.0, "carbs": 0.0, "fat": 0.0},
        )
