from django.test import override_settings

from mobile_api.tests.base import PaidMobileAPITestCase
from notas.domain.models import Food, Meal, MealFood


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIFoodVisualTests(PaidMobileAPITestCase):
    def test_food_visuals_are_exposed_in_picker_library_and_composition_payloads(self):
        food = Food.objects.create(
            name="Pechuga de pollo",
            protein=31,
            carbs=0,
            fat=3.6,
            created_by=self.user,
        )
        meal = Meal.objects.create(name="Almuerzo", created_by=self.user, is_draft=False)
        MealFood.objects.create(meal=meal, food=food, quantity=120)

        picker = self.client.get("/api/v1/foods", {"search": "Pechuga"}).json()["data"]["items"][0]
        library = self.client.get("/api/v1/library/foods").json()["data"]["items"][0]
        composition = self.client.get(f"/api/v1/library/meals/{meal.id}").json()["data"]["panel"]["foods"][0]

        for payload in (picker, library, composition):
            self.assertEqual(payload["emoji"], "🍗")
            self.assertEqual(payload["visual_key"], "chicken_breast")
