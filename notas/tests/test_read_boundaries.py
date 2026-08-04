from django.contrib.auth.models import User
from django.http import Http404
from django.test import TestCase

from notas.application.queries.read_boundaries import (
    get_readable_dailyplan_or_404,
    get_readable_dailyplan_queryset,
    get_readable_food_or_404,
    get_readable_food_queryset,
    get_readable_meal_or_404,
    get_readable_meal_queryset,
)
from notas.application.services.access.access import (
    get_dailyplan_for_user,
    get_meal_for_user,
)
from notas.domain.models import (
    DailyPlan,
    DailyPlanShare,
    Food,
    Meal,
    MealShare,
)


class ReadBoundaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@example.com",
            password="pass123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="pass123",
        )

        self.user_food = Food.objects.create(
            name="User Food",
            protein=10,
            carbs=20,
            fat=5,
            created_by=self.user,
        )
        self.system_food = Food.objects.create(
            name="System Food",
            protein=5,
            carbs=10,
            fat=1,
            created_by=None,
        )
        self.other_food = Food.objects.create(
            name="Other Food",
            protein=1,
            carbs=1,
            fat=1,
            created_by=self.other_user,
        )
        self.global_other_food = Food.objects.create(
            name="Global Other Food",
            protein=20,
            carbs=10,
            fat=2,
            created_by=self.other_user,
            is_global=True,
        )

        self.user_meal = Meal.objects.create(
            name="User Meal",
            created_by=self.user,
            is_public=False,
            is_draft=False,
        )
        self.public_meal = Meal.objects.create(
            name="Public Meal",
            created_by=self.other_user,
            is_public=True,
            is_draft=False,
        )
        self.public_draft_meal = Meal.objects.create(
            name="Public Draft Meal",
            created_by=self.other_user,
            is_public=True,
            is_draft=True,
        )
        self.private_other_meal = Meal.objects.create(
            name="Private Other Meal",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
        )
        self.shared_meal = Meal.objects.create(
            name="Shared Meal",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
        )
        self.removed_shared_meal = Meal.objects.create(
            name="Removed Shared Meal",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
        )

        MealShare.objects.create(
            meal=self.shared_meal,
            sender=self.other_user,
            recipient_email=self.user.email,
            accepted_by=self.user,
            dismissed=False,
            removed=False,
        )
        MealShare.objects.create(
            meal=self.removed_shared_meal,
            sender=self.other_user,
            recipient_email=self.user.email,
            accepted_by=self.user,
            dismissed=False,
            removed=True,
        )

        self.user_dailyplan = DailyPlan.objects.create(
            name="User DailyPlan",
            created_by=self.user,
            is_public=False,
            is_draft=False,
        )
        self.public_dailyplan = DailyPlan.objects.create(
            name="Public DailyPlan",
            created_by=self.other_user,
            is_public=True,
            is_draft=False,
        )
        self.public_draft_dailyplan = DailyPlan.objects.create(
            name="Public Draft DailyPlan",
            created_by=self.other_user,
            is_public=True,
            is_draft=True,
        )
        self.private_other_dailyplan = DailyPlan.objects.create(
            name="Private Other DailyPlan",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
        )
        self.shared_dailyplan = DailyPlan.objects.create(
            name="Shared DailyPlan",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
        )
        self.removed_shared_dailyplan = DailyPlan.objects.create(
            name="Removed Shared DailyPlan",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
        )

        DailyPlanShare.objects.create(
            dailyplan=self.shared_dailyplan,
            sender=self.other_user,
            recipient_email=self.user.email,
            accepted_by=self.user,
            dismissed=False,
            removed=False,
        )
        DailyPlanShare.objects.create(
            dailyplan=self.removed_shared_dailyplan,
            sender=self.other_user,
            recipient_email=self.user.email,
            accepted_by=self.user,
            dismissed=False,
            removed=True,
        )

    def test_readable_food_queryset_includes_user_and_system_foods_only(self):
        foods = get_readable_food_queryset(self.user)

        names = [food.name for food in foods]

        self.assertIn("User Food", names)
        self.assertIn("System Food", names)
        self.assertIn("Global Other Food", names)
        self.assertNotIn("Other Food", names)




    def test_readable_food_or_404_blocks_other_user_food(self):
        with self.assertRaises(Http404):
            get_readable_food_or_404(
                self.user,
                self.other_food.id,
            )

    def test_readable_meal_queryset_applies_public_and_share_boundaries(self):
        meals = get_readable_meal_queryset(self.user)

        names = [meal.name for meal in meals]

        self.assertIn("User Meal", names)
        self.assertIn("Public Meal", names)
        self.assertIn("Shared Meal", names)
        self.assertNotIn("Public Draft Meal", names)
        self.assertNotIn("Private Other Meal", names)
        self.assertNotIn("Removed Shared Meal", names)

    def test_readable_meal_or_404_blocks_private_or_removed_meals(self):
        with self.assertRaises(Http404):
            get_readable_meal_or_404(
                self.user,
                self.private_other_meal.id,
            )

        with self.assertRaises(Http404):
            get_readable_meal_or_404(
                self.user,
                self.removed_shared_meal.id,
            )

    def test_readable_dailyplan_queryset_applies_public_and_share_boundaries(self):
        dailyplans = get_readable_dailyplan_queryset(self.user)

        names = [dailyplan.name for dailyplan in dailyplans]

        self.assertIn("User DailyPlan", names)
        self.assertIn("Public DailyPlan", names)
        self.assertIn("Shared DailyPlan", names)
        self.assertNotIn("Public Draft DailyPlan", names)
        self.assertNotIn("Private Other DailyPlan", names)
        self.assertNotIn("Removed Shared DailyPlan", names)

    def test_readable_dailyplan_or_404_blocks_private_or_removed_dailyplans(self):
        with self.assertRaises(Http404):
            get_readable_dailyplan_or_404(
                self.user,
                self.private_other_dailyplan.id,
            )

        with self.assertRaises(Http404):
            get_readable_dailyplan_or_404(
                self.user,
                self.removed_shared_dailyplan.id,
            )

    def test_legacy_access_service_uses_same_meal_boundary(self):
        meal = get_meal_for_user(
            self.user,
            self.shared_meal.id,
        )

        self.assertEqual(meal.id, self.shared_meal.id)

        with self.assertRaises(Meal.DoesNotExist):
            get_meal_for_user(
                self.user,
                self.removed_shared_meal.id,
            )

    def test_legacy_access_service_uses_same_dailyplan_boundary(self):
        dailyplan = get_dailyplan_for_user(
            self.user,
            self.shared_dailyplan.id,
        )

        self.assertEqual(dailyplan.id, self.shared_dailyplan.id)

        with self.assertRaises(DailyPlan.DoesNotExist):
            get_dailyplan_for_user(
                self.user,
                self.removed_shared_dailyplan.id,
            )