from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from mobile_api.selectors import library_meals_payload
from mobile_api.tests.base import PaidMobileAPITestCase
from notas.domain.models import Food, Meal, MealFood


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class LibraryProjectionPerformanceTests(PaidMobileAPITestCase):
    def test_meal_cards_have_a_constant_query_budget(self):
        food = Food.objects.create(name="Avena", protein=13, carbs=68, fat=7, created_by=self.user)
        for index in range(12):
            meal = Meal.objects.create(name=f"Comida {index}", created_by=self.user, is_draft=False)
            MealFood.objects.create(meal=meal, food=food, quantity=100)

        with CaptureQueriesContext(connection) as queries:
            payload = library_meals_payload(self.user, limit=12, include_actions=False)

        self.assertEqual(len(payload["items"]), 12)
        self.assertLessEqual(len(queries), 5)
