from django.template.loader import render_to_string
from django.test import SimpleTestCase


class NutritionPanelDistributionTests(SimpleTestCase):
    def setUp(self):
        self.items = [
            {
                "rel": {
                    "name": "Avena",
                    "ppk": 0.25,
                    "g_protein": 20,
                    "g_carbs": 40,
                    "g_fat": 10,
                    "kcal_distribution": {"protein": 24, "carbs": 48, "fat": 28},
                }
            }
        ]

    def test_macros_panel_moves_ppk_before_grams_and_omits_distribution_bar(self):
        rendered = render_to_string("components/grid_foods_mobile_macros.html", {"items": self.items})

        self.assertLess(rendered.index("PpK"), rendered.index(">P<"))
        self.assertIn("program-week-day-table__ppk-value", rendered)
        self.assertNotIn("macro-kcal-distribution", rendered)

    def test_dist_panel_keeps_percentages_and_distribution_bar(self):
        rendered = render_to_string("components/grid_foods_mobile_distribution.html", {"items": self.items})

        self.assertIn("24%", rendered)
        self.assertIn("48%", rendered)
        self.assertIn("28%", rendered)
        self.assertIn("macro-kcal-distribution", rendered)

    def test_shared_mobile_tabs_expose_dist_between_macros_and_alloc(self):
        rendered = render_to_string("components/detail_tabs_foods.html", {"panel_id": "nutrition"})

        self.assertLess(rendered.index("Macros"), rendered.index("Dist"))
        self.assertLess(rendered.index("Dist"), rendered.index("Alloc"))
