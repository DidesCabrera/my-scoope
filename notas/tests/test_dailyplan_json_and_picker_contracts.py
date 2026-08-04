import json
from datetime import time

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from notas.application.services.commands.dailyplan_commands import (
    copy_dailyplan,
    fork_dailyplan,
    save_dailyplan,
)
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood

User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class DailyPlanJsonAndPickerContractTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@test.com",
            password="12345678",
        )

        self.client = Client()
        self.client.login(
            username="felipe",
            password="12345678",
        )

    def test_dailyplan_domain_properties_sum_meal_values(self):
        dailyplan = DailyPlan.objects.create(
            name="Plan A",
            created_by=self.user,
            is_draft=False,
        )

        meal_1 = Meal.objects.create(
            name="Breakfast",
            created_by=self.user,
            is_draft=False,
        )
        meal_2 = Meal.objects.create(
            name="Lunch",
            created_by=self.user,
            is_draft=False,
        )

        food_1 = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )
        food_2 = Food.objects.create(
            name="Rice",
            protein=2,
            carbs=30,
            fat=1,
            created_by=self.user,
        )

        MealFood.objects.create(
            meal=meal_1,
            food=food_1,
            quantity=100,
        )
        MealFood.objects.create(
            meal=meal_2,
            food=food_2,
            quantity=100,
        )

        meal_1.refresh_from_db()
        meal_2.refresh_from_db()

        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal_1,
            hour=time(8, 0),
            order=1,
        )
        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal_2,
            hour=time(13, 0),
            order=2,
        )

        self.assertEqual(dailyplan.protein, meal_1.protein + meal_2.protein)
        self.assertEqual(dailyplan.carbs, meal_1.carbs + meal_2.carbs)
        self.assertEqual(dailyplan.fat, meal_1.fat + meal_2.fat)
        self.assertEqual(dailyplan.total_kcal, meal_1.total_kcal + meal_2.total_kcal)

    def test_dailyplan_meal_slots_keep_order_and_metadata(self):
        dailyplan = DailyPlan.objects.create(
            name="Plan A",
            created_by=self.user,
            is_draft=False,
        )

        meal_1 = Meal.objects.create(
            name="Breakfast",
            created_by=self.user,
            is_draft=False,
        )
        meal_2 = Meal.objects.create(
            name="Lunch",
            created_by=self.user,
            is_draft=False,
        )

        dpm_1 = DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal_1,
            hour=time(8, 30),
            note="Morning slot",
            order=1,
        )
        dpm_2 = DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal_2,
            hour=time(13, 15),
            note="Lunch slot",
            order=2,
        )

        ordered = list(dailyplan.dailyplan_meals.order_by("order", "id"))

        self.assertEqual(ordered[0].id, dpm_1.id)
        self.assertEqual(ordered[1].id, dpm_2.id)

        self.assertEqual(ordered[0].note, "Morning slot")
        self.assertEqual(ordered[1].note, "Lunch slot")
        self.assertEqual(ordered[0].hour, time(8, 30))
        self.assertEqual(ordered[1].hour, time(13, 15))

    def test_dailyplan_fork_flags_follow_expected_contract(self):
        author = User.objects.create_user(
            username="author",
            email="author@test.com",
            password="12345678",
        )

        original = DailyPlan.objects.create(
            name="Original plan",
            created_by=author,
            is_draft=False,
            is_public=True,
            is_forkable=True,
            is_copiable=False,
        )

        forked = fork_dailyplan(original, self.user)

        self.assertNotEqual(forked.id, original.id)
        self.assertEqual(forked.created_by, self.user)
        self.assertEqual(forked.forked_from, original)
        self.assertEqual(forked.original_author, author)

        self.assertFalse(forked.is_public)
        self.assertTrue(forked.is_forkable)
        self.assertFalse(forked.is_copiable)
        self.assertFalse(forked.is_draft)

    def test_dailyplan_meal_snapshot_in_fork_is_json_serializable_by_structure(self):
        author = User.objects.create_user(
            username="author2",
            email="author2@test.com",
            password="12345678",
        )

        meal = Meal.objects.create(
            name="Meal A",
            created_by=author,
            is_draft=False,
            protein_cached=20,
            carbs_cached=30,
            fat_cached=10,
            total_kcal_cached=290,
            alloc_protein_cached=27.5,
            alloc_carbs_cached=41.3,
            alloc_fat_cached=31.2,
            foods_aggregation_cached=[
                {"name": "Egg", "quantity": 100},
            ],
        )

        dailyplan = DailyPlan.objects.create(
            name="Plan A",
            created_by=author,
            is_draft=False,
            is_public=True,
            is_forkable=True,
            is_copiable=False,
        )

        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal,
            order=1,
        )

        forked = fork_dailyplan(dailyplan, self.user)

        dpm = forked.dailyplan_meals.first()

        payload = {
            "dailyplan_id": forked.id,
            "meal": {
                "id": dpm.meal.id,
                "name": dpm.meal.name,
                "protein": dpm.meal.protein_cached,
                "carbs": dpm.meal.carbs_cached,
                "fat": dpm.meal.fat_cached,
                "total_kcal": dpm.meal.total_kcal_cached,
                "alloc": {
                    "protein": dpm.meal.alloc_protein_cached,
                    "carbs": dpm.meal.alloc_carbs_cached,
                    "fat": dpm.meal.alloc_fat_cached,
                },
                "foods": dpm.meal.foods_aggregation_cached,
            },
        }

        serialized = json.dumps(payload)

        self.assertIn("Meal A", serialized)
        self.assertIn('"dailyplan_id"', serialized)
        self.assertIn('"meal"', serialized)
        self.assertIn('"foods"', serialized)

        self.assertEqual(payload["meal"]["id"], dpm.meal.id)
        self.assertEqual(payload["meal"]["name"], "Meal A")


    def test_dailyplan_ordered_slots_can_be_projected_consistently(self):
        dailyplan = DailyPlan.objects.create(
            name="Plan Ordered",
            created_by=self.user,
            is_draft=False,
        )

        meal_1 = Meal.objects.create(
            name="Meal 1",
            created_by=self.user,
            is_draft=False,
        )
        meal_2 = Meal.objects.create(
            name="Meal 2",
            created_by=self.user,
            is_draft=False,
        )
        meal_3 = Meal.objects.create(
            name="Meal 3",
            created_by=self.user,
            is_draft=False,
        )

        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal_2,
            order=2,
        )
        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal_1,
            order=1,
        )
        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal_3,
            order=3,
        )

        names = [
            dpm.meal.name
            for dpm in dailyplan.dailyplan_meals.order_by("order", "id")
        ]

        self.assertEqual(names, ["Meal 1", "Meal 2", "Meal 3"])
