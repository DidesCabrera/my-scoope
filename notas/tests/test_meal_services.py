from django.contrib.auth import get_user_model
from django.test import TestCase

from notas.application.services.commands.meal_commands import fork_meal
from notas.domain.models import Food, Meal, MealFood

User = get_user_model()


class MealServiceTests(TestCase):

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

    def test_fork_meal_creates_new_meal_for_target_user(self):
        original = Meal.objects.create(
            name="Original meal",
            created_by=self.author,
            is_public=True,
            is_forkable=True,
            is_copiable=False,
            is_draft=False,
        )

        food = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.author,
        )

        MealFood.objects.create(
            meal=original,
            food=food,
            quantity=100,
        )

        forked = fork_meal(original, self.other_user)

        self.assertNotEqual(original.id, forked.id)
        self.assertEqual(forked.created_by, self.other_user)
        self.assertEqual(forked.forked_from, original)
        self.assertEqual(forked.original_author, self.author)
        self.assertEqual(forked.name, original.name)

        self.assertEqual(forked.meal_food_set.count(), 1)

        forked_meal_food = forked.meal_food_set.first()
        self.assertEqual(forked_meal_food.food, food)
        self.assertEqual(forked_meal_food.quantity, 100)

        self.assertFalse(forked.is_public)
        self.assertTrue(forked.is_forkable)
        self.assertFalse(forked.is_copiable)
        self.assertFalse(forked.is_draft)