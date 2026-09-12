from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.queries.dailyplan_queries import (
    get_dailyplan_detail,
    list_available_dailyplans,
    list_user_dailyplans,
    search_dailyplans,
)
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    DailyPlanShare,
    Food,
    Meal,
    MealFood,
)


class DailyPlanQueryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            password="pass123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="pass123",
        )

        self.egg = Food.objects.create(
            name="Egg",
            protein=13,
            carbs=1,
            fat=11,
            created_by=self.user,
        )

        self.rice = Food.objects.create(
            name="Rice",
            protein=2.7,
            carbs=28,
            fat=0.3,
            created_by=self.user,
        )

        self.breakfast = Meal.objects.create(
            name="Breakfast",
            created_by=self.user,
            is_public=False,
            is_draft=False,
        )

        MealFood.objects.create(
            meal=self.breakfast,
            food=self.egg,
            quantity=100,
            order=1,
        )

        MealFood.objects.create(
            meal=self.breakfast,
            food=self.rice,
            quantity=200,
            order=2,
        )

        self.user_dailyplan = DailyPlan.objects.create(
            name="Training Day",
            created_by=self.user,
            is_public=False,
            is_draft=False,
        )

        DailyPlanMeal.objects.create(
            dailyplan=self.user_dailyplan,
            meal=self.breakfast,
            hour="08:00",
            note="Morning meal",
            order=1,
        )

        self.public_dailyplan = DailyPlan.objects.create(
            name="Public Plan",
            created_by=self.other_user,
            is_public=True,
            is_draft=False,
            is_forkable=True,
        )

        self.private_other_dailyplan = DailyPlan.objects.create(
            name="Private Other Plan",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
        )

        self.shared_dailyplan = DailyPlan.objects.create(
            name="Shared Plan",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
        )

        DailyPlanShare.objects.create(
            dailyplan=self.shared_dailyplan,
            sender=self.other_user,
            recipient_email="felipe@example.com",
            accepted_by=self.user,
        )

    def test_list_user_dailyplans_returns_only_user_dailyplans(self):
        dailyplans = list_user_dailyplans(self.user)

        names = [dailyplan.name for dailyplan in dailyplans]

        self.assertEqual(names, ["Training Day"])
        self.assertNotIn("Public Plan", names)
        self.assertNotIn("Private Other Plan", names)
        self.assertNotIn("Shared Plan", names)

    def test_list_available_dailyplans_excludes_shared_source_objects(self):
        dailyplans = list_available_dailyplans(self.user)

        names = [dailyplan.name for dailyplan in dailyplans]

        self.assertIn("Training Day", names)
        self.assertIn("Public Plan", names)
        self.assertNotIn("Shared Plan", names)
        self.assertNotIn("Private Other Plan", names)

    def test_search_dailyplans_filters_available_dailyplans(self):
        dailyplans = search_dailyplans(self.user, "public")

        names = [dailyplan.name for dailyplan in dailyplans]

        self.assertEqual(names, ["Public Plan"])

    def test_get_dailyplan_detail_returns_serializable_dto(self):
        dailyplan = get_dailyplan_detail(
            self.user,
            self.user_dailyplan.id,
        )

        data = dailyplan.as_dict()

        self.assertEqual(data["id"], self.user_dailyplan.id)
        self.assertEqual(data["name"], "Training Day")
        self.assertEqual(data["meals_count"], 1)
        self.assertEqual(data["foods_count"], 2)
        self.assertEqual(len(data["meals"]), 1)
        self.assertEqual(data["meals"][0]["meal_name"], "Breakfast")
        self.assertEqual(data["meals"][0]["foods_count"], 2)
        self.assertEqual(len(data["foods_aggregation"]), 2)
        self.assertIn("total_kcal", data["kpis"])
        self.assertIn("alloc_protein", data["kpis"])

    def test_get_dailyplan_detail_allows_public_dailyplan(self):
        dailyplan = get_dailyplan_detail(
            self.user,
            self.public_dailyplan.id,
        )

        self.assertEqual(dailyplan.name, "Public Plan")

    def test_get_dailyplan_detail_blocks_shared_source_object(self):
        with self.assertRaises(Exception):
            get_dailyplan_detail(self.user, self.shared_dailyplan.id)

    def test_get_dailyplan_detail_blocks_private_other_dailyplan(self):
        with self.assertRaises(Exception):
            get_dailyplan_detail(
                self.user,
                self.private_other_dailyplan.id,
            )
