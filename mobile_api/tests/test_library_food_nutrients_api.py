from django.test import override_settings

from mobile_api.tests.base import PaidMobileAPITestCase
from notas.domain.models import Food


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIFoodNutrientsTests(PaidMobileAPITestCase):
    def test_manual_food_optional_nutrients_can_be_created_edited_and_cleared(self):
        created = self.client.post(
            "/api/v1/library/foods",
            data={"name": "Yogur", "protein": 10, "carbs": 5, "fat": 3, "saturated_fat_g": 1.2, "sugar_g": 4, "fiber_g": 0, "sodium_mg": 125},
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 200)
        food_id = created.json()["data"]["id"]
        self.assertEqual(created.json()["data"]["food_nutrition"], {"saturated_fat_g": 1.2, "sugar_g": 4.0, "fiber_g": 0.0, "sodium_mg": 125.0})

        updated = self.client.put(
            f"/api/v1/library/foods/{food_id}/edit",
            data={"name": "Yogur natural", "protein": 11, "carbs": 5, "fat": 3, "saturated_fat_g": None, "sugar_g": 3.5},
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["food_nutrition"], {"saturated_fat_g": None, "sugar_g": 3.5, "fiber_g": 0.0, "sodium_mg": 125.0})

        food = Food.objects.get(pk=food_id)
        self.assertEqual((food.protein, food.carbs, food.fat), (11, 5, 3))

        minimal = self.client.post(
            "/api/v1/library/foods",
            data={"name": "Avena", "protein": 13, "carbs": 68, "fat": 7},
            content_type="application/json",
        )
        self.assertEqual(minimal.status_code, 200)
        self.assertEqual(minimal.json()["data"]["food_nutrition"], {"saturated_fat_g": None, "sugar_g": None, "fiber_g": None, "sodium_mg": None})

