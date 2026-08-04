from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase

from notas.application.services.commands.dailyplan_commands import fork_dailyplan, save_dailyplan
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood

User = get_user_model()


class DailyPlanServiceTests(TestCase):

    def setUp(self):
        self.author = User.objects.create_user(
            username="author",
            email="author@test.com",
            password="12345678",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="12345678",
        )

    def test_fork_dailyplan_creates_new_plan_for_target_user(self):
        meal = Meal.objects.create(
            name="Breakfast",
            created_by=self.author,
            is_public=True,
            is_forkable=True,
            is_copiable=False,
            is_draft=False,
        )

        dailyplan = DailyPlan.objects.create(
            name="Cut plan",
            created_by=self.author,
            is_public=True,
            is_forkable=True,
            is_copiable=False,
            is_draft=False,
        )

        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal,
            note="Pre workout",
            hour=time(8, 30),
            order=1,
        )

        forked = fork_dailyplan(dailyplan, self.other_user)

        self.assertNotEqual(dailyplan.id, forked.id)
        self.assertEqual(forked.created_by, self.other_user)
        self.assertEqual(forked.forked_from, dailyplan)
        self.assertEqual(forked.original_author, self.author)
        self.assertEqual(forked.name, dailyplan.name)

        self.assertFalse(forked.is_public)
        self.assertTrue(forked.is_forkable)
        self.assertFalse(forked.is_copiable)
        self.assertFalse(forked.is_draft)

    def test_fork_dailyplan_clones_dailyplan_meals_with_same_slot_data(self):
        meal = Meal.objects.create(
            name="Breakfast",
            created_by=self.author,
            is_draft=False,
        )

        dailyplan = DailyPlan.objects.create(
            name="Plan A",
            created_by=self.author,
            is_draft=False,
        )

        original_dpm = DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal,
            note="Morning meal",
            hour=time(9, 0),
            order=2,
        )

        forked = fork_dailyplan(dailyplan, self.other_user)

        self.assertEqual(forked.dailyplan_meals.count(), 1)

        forked_dpm = forked.dailyplan_meals.first()

        self.assertNotEqual(original_dpm.id, forked_dpm.id)
        self.assertEqual(forked_dpm.dailyplan, forked)
        self.assertNotEqual(forked_dpm.meal.id, meal.id)
        self.assertEqual(forked_dpm.meal.created_by, self.other_user)
        self.assertEqual(forked_dpm.meal.forked_from, meal)
        self.assertEqual(forked_dpm.meal.original_author, self.author)
        self.assertEqual(forked_dpm.meal.name, meal.name)

        self.assertEqual(forked_dpm.note, "Morning meal")
        self.assertEqual(forked_dpm.hour, time(9, 0))
        self.assertEqual(forked_dpm.order, 2)

    def test_save_dailyplan_behaves_like_fork(self):
        meal = Meal.objects.create(
            name="Lunch",
            created_by=self.author,
            is_draft=False,
        )

        dailyplan = DailyPlan.objects.create(
            name="Plan Save",
            created_by=self.author,
            is_public=True,
            is_forkable=True,
            is_copiable=False,
            is_draft=False,
        )

        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal,
            note="Midday",
            hour=time(13, 0),
            order=1,
        )

        saved = save_dailyplan(dailyplan, self.other_user)

        self.assertNotEqual(saved.id, dailyplan.id)
        self.assertEqual(saved.created_by, self.other_user)
        self.assertEqual(saved.forked_from, dailyplan)
        self.assertEqual(saved.original_author, self.author)
        self.assertEqual(saved.dailyplan_meals.count(), 1)

    def test_dailyplan_totals_sum_meal_macros(self):
        dailyplan = DailyPlan.objects.create(
            name="Macro plan",
            created_by=self.author,
            is_draft=False,
        )

        meal_1 = Meal.objects.create(
            name="Meal 1",
            created_by=self.author,
            is_draft=False,
        )
        meal_2 = Meal.objects.create(
            name="Meal 2",
            created_by=self.author,
            is_draft=False,
        )

        food_1 = Food.objects.create(
            name="Chicken",
            protein=20,
            carbs=0,
            fat=5,
            created_by=self.author,
        )
        food_2 = Food.objects.create(
            name="Rice",
            protein=2,
            carbs=30,
            fat=1,
            created_by=self.author,
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
            order=1,
        )
        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal_2,
            order=2,
        )

        self.assertEqual(dailyplan.protein, meal_1.protein + meal_2.protein)
        self.assertEqual(dailyplan.carbs, meal_1.carbs + meal_2.carbs)
        self.assertEqual(dailyplan.fat, meal_1.fat + meal_2.fat)
        self.assertEqual(dailyplan.total_kcal, meal_1.total_kcal + meal_2.total_kcal)