from django.contrib.auth import get_user_model
from django.test import TestCase

from notas.application.services.cache.dailyplan_summary import (
    DAILYPLAN_SUMMARY_CACHE_VERSION,
    build_dailyplan_summary,
)
from notas.application.services.cache.program_summary import (
    PROGRAM_SUMMARY_CACHE_VERSION,
    build_program_summary,
)
from notas.domain.models import DailyPlanMeal, Program, ProgramDay
from notas.tests.builders import attach_food, create_dailyplan, create_food, create_meal

User = get_user_model()


class SummaryCacheEnergyMetricsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="energy-cache-user",
            email="energy-cache@example.com",
            password="test-pass-123",
        )
        cls.food = create_food(
            created_by=cls.user,
            name="Balanced food",
            protein=20,
            carbs=10,
            fat=5,
        )
        cls.meal = create_meal(created_by=cls.user, name="Balanced meal")
        attach_food(meal=cls.meal, food=cls.food, quantity=100)
        cls.dailyplan = create_dailyplan(created_by=cls.user, name="Energy day")
        DailyPlanMeal.objects.create(dailyplan=cls.dailyplan, meal=cls.meal)
        cls.program = Program.objects.create(
            name="Energy program",
            created_by=cls.user,
            duration_weeks=1,
        )
        ProgramDay.objects.create(
            program=cls.program,
            dailyplan=cls.dailyplan,
            week_number=1,
            day_number=1,
        )

    def assert_distribution_contract(self, row):
        distribution = row["rel"]["kcal_distribution"]
        self.assertAlmostEqual(sum(distribution.values()), 100.0)
        self.assertAlmostEqual(distribution["protein"], 80 / 165 * 100)
        self.assertAlmostEqual(distribution["carbs"], 40 / 165 * 100)
        self.assertAlmostEqual(distribution["fat"], 45 / 165 * 100)

    def test_dailyplan_summary_projects_distribution_to_meals_and_foods(self):
        summary = build_dailyplan_summary(self.dailyplan)

        self.assertEqual(summary["version"], DAILYPLAN_SUMMARY_CACHE_VERSION)
        self.assert_distribution_contract(summary["meals"][0]["table_item"])
        self.assert_distribution_contract(summary["foods_aggregation_table"][0])

    def test_program_summary_projects_distribution_to_food_aggregations(self):
        summary = build_program_summary(self.program)

        self.assertEqual(summary["version"], PROGRAM_SUMMARY_CACHE_VERSION)
        self.assert_distribution_contract(summary["program_foods_aggregation_table"][0])
        self.assert_distribution_contract(summary["weeks"][0]["foods_aggregation_table"][0])
