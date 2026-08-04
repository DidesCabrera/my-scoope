from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.domain.models import DailyPlan, Food, Meal, MealFood

User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MealViewTests(TestCase):

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

    def test_meal_create_creates_draft_meal(self):
        response = self.client.post(
            reverse("meal_create"),
            data={
                "name": "New meal",
            },
        )

        self.assertEqual(response.status_code, 302)

        meal = Meal.objects.get(name="New meal")

        self.assertEqual(meal.created_by, self.user)
        self.assertTrue(meal.is_draft)

    def test_meal_create_from_dailyplan_sets_pending_dailyplan(self):
        dailyplan = DailyPlan.objects.create(
            name="Plan 1",
            created_by=self.user,
            is_draft=False,
        )

        response = self.client.post(
            reverse("meal_create") + f"?from_dailyplan={dailyplan.id}",
            data={
                "name": "Meal from plan",
            },
        )

        self.assertEqual(response.status_code, 302)

        meal = Meal.objects.get(name="Meal from plan")

        self.assertEqual(meal.pending_dailyplan, dailyplan)
        self.assertTrue(meal.is_draft)

    def test_meal_detail_save_food_creates_mealfood(self):
        meal = Meal.objects.create(
            name="Editable meal",
            created_by=self.user,
            is_draft=True,
        )

        food = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        response = self.client.post(
            reverse("meal_detail", args=[meal.id]),
            data={
                "save_food": "1",
                "food_id": food.id,
                "quantity": 100,
            },
        )

        self.assertEqual(response.status_code, 302)

        meal.refresh_from_db()

        self.assertEqual(meal.meal_food_set.count(), 1)

        meal_food = meal.meal_food_set.first()
        self.assertEqual(meal_food.food, food)
        self.assertEqual(meal_food.quantity, 100)

        self.assertFalse(meal.is_draft)

    def test_meal_detail_save_food_updates_existing_mealfood(self):
        meal = Meal.objects.create(
            name="Editable meal",
            created_by=self.user,
            is_draft=False,
        )

        food = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        meal_food = MealFood.objects.create(
            meal=meal,
            food=food,
            quantity=100,
        )

        response = self.client.post(
            reverse("meal_detail", args=[meal.id]),
            data={
                "save_food": "1",
                "mealfood_id": meal_food.id,
                "food_id": food.id,
                "quantity": 150,
            },
        )

        self.assertEqual(response.status_code, 302)

        meal_food.refresh_from_db()
        self.assertEqual(meal_food.quantity, 150)

    def test_meal_detail_finish_for_dailyplan_clears_pending_dailyplan(self):
        dailyplan = DailyPlan.objects.create(
            name="Plan 1",
            created_by=self.user,
            is_draft=False,
        )

        meal = Meal.objects.create(
            name="Meal from plan",
            created_by=self.user,
            is_draft=False,
            pending_dailyplan=dailyplan,
        )

        response = self.client.post(
            reverse("meal_detail", args=[meal.id]),
            data={
                "finish_for_dailyplan": "1",
            },
        )

        self.assertEqual(response.status_code, 302)

        meal.refresh_from_db()
        self.assertIsNone(meal.pending_dailyplan)

    def test_meal_fork_creates_library_fork(self):
        author = User.objects.create_user(
            username="author",
            email="author@test.com",
            password="12345678",
        )

        original = Meal.objects.create(
            name="Original meal",
            created_by=author,
            is_draft=False,
            is_public=True,
            is_forkable=True,
            is_copiable=False,
        )

        response = self.client.post(
            reverse("meal_fork", args=[original.id])
        )

        self.assertEqual(response.status_code, 302)

        forked = Meal.objects.exclude(id=original.id).get()

        self.assertEqual(forked.created_by, self.user)
        self.assertEqual(forked.forked_from, original)
        self.assertEqual(forked.original_author, author)

    def test_meal_remove_deletes_meal(self):
        meal = Meal.objects.create(
            name="Meal to remove",
            created_by=self.user,
            is_draft=False,
        )

        response = self.client.post(
            reverse("meal_remove", args=[meal.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Meal.objects.filter(id=meal.id).exists())

    def test_meal_draft_delete_only_deletes_draft_meal(self):
        meal = Meal.objects.create(
            name="Draft meal",
            created_by=self.user,
            is_draft=True,
        )

        response = self.client.post(
            reverse("meal_draft_delete", args=[meal.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Meal.objects.filter(id=meal.id).exists())

    def test_meal_configure_redirects_when_user_has_no_distribution_access(self):
        meal = Meal.objects.create(
            name="Config meal",
            created_by=self.user,
            is_draft=False,
        )

        response = self.client.get(
            reverse("meal_configure", args=[meal.id])
        )

        self.assertEqual(response.status_code, 302)

        meal.refresh_from_db()
        self.assertFalse(meal.is_public)
        self.assertTrue(meal.is_forkable)
        self.assertFalse(meal.is_copiable)
