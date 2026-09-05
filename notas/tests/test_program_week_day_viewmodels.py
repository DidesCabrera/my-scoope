from types import SimpleNamespace

from django.test import SimpleTestCase

from notas.presentation.viewmodels.programs import (
    build_program_day_card_actions,
    build_program_week_summary_metrics,
    build_week_day_nutrition_rows,
)


class ProgramWeekDayNutritionRowsTests(SimpleTestCase):
    def test_dailyplan_detail_is_the_last_selected_day_action(self):
        dailyplan = SimpleNamespace(id=20)
        program_day = SimpleNamespace(id=10, program_id=8, week_number=2, day_number=1)

        actions = build_program_day_card_actions(dailyplan, program_day)

        self.assertEqual([action["key"] for action in actions], ["replace", "remove", "detail"])
        self.assertEqual(actions[-1]["url"], "/app/dailyplans/20/?program_day=10")

    def test_separates_week_alloc_from_daily_macro_distribution(self):
        week = {
            "totals": {
                "total_kcal": 2500,
                "kcal_protein": 500,
                "kcal_carbs": 1000,
                "kcal_fat": 1000,
            },
            "days": [
                {
                    "day_number": 1,
                    "program_day": {"id": 10},
                    "dailyplan": {"id": 20, "name": "Plan A"},
                    "snapshot": {
                        "total_kcal": 1000,
                        "protein": 50,
                        "carbs": 100,
                        "fat": 40,
                        "kcal_protein": 200,
                        "kcal_carbs": 400,
                        "kcal_fat": 400,
                        "alloc": {"protein": 20, "carbs": 40, "fat": 40},
                    },
                }
            ],
        }

        row = build_week_day_nutrition_rows(week)[0]

        self.assertEqual(row["kcal_share"], 40)
        self.assertEqual(row["kcal_distribution"], {"protein": 20, "carbs": 40, "fat": 40})
        self.assertEqual(row["alloc"], {"protein": 40, "carbs": 40, "fat": 40})
        self.assertEqual(row["kcal_protein"], 200)
        self.assertEqual(row["kcal_carbs"], 400)
        self.assertEqual(row["kcal_fat"], 400)

    def test_builds_assigned_day_average_and_previous_week_ratio(self):
        weeks = [
            {"filled_days_count": 2, "totals": {"total_kcal": 4000}},
            {"filled_days_count": 4, "totals": {"total_kcal": 10000}},
        ]

        enriched = build_program_week_summary_metrics(weeks)

        self.assertEqual(enriched[0]["assigned_dailyplans_count"], 2)
        self.assertEqual(enriched[0]["average_kcal_per_assigned_day"], 2000)
        self.assertIsNone(enriched[0]["previous_week_average_ratio"])
        self.assertEqual(enriched[1]["assigned_dailyplans_count"], 4)
        self.assertEqual(enriched[1]["average_kcal_per_assigned_day"], 2500)
        self.assertEqual(enriched[1]["previous_week_average_ratio"], 25)
