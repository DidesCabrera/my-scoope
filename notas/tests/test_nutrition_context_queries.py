from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.queries.nutrition_context_queries import (
    get_user_nutrition_context,
)


class NutritionContextQueryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            password="pass123",
        )

    def test_get_user_nutrition_context_without_weight(self):
        context = get_user_nutrition_context(self.user)

        data = context.as_dict()

        self.assertEqual(data["user_id"], self.user.id)
        self.assertEqual(data["username"], "felipe")
        self.assertEqual(data["current_weight"], 75.0)
        self.assertTrue(data["has_current_weight"])

    def test_get_user_nutrition_context_is_serializable(self):
        context = get_user_nutrition_context(self.user)

        data = context.as_dict()

        self.assertIsInstance(data, dict)
        self.assertIn("user_id", data)
        self.assertIn("username", data)
        self.assertIn("current_weight", data)
        self.assertIn("has_current_weight", data)