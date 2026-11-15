from django.test import override_settings

from mobile_api.tests.base import PaidMobileAPITestCase
from notas.domain.models import Food, FoodPortion


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class FoodPortionContractAPITests(PaidMobileAPITestCase):
    def test_personal_food_suggested_portion_and_household_equivalence_round_trip(self):
        created = self.client.post(
            "/api/v1/library/foods",
            data={"name": "Proteína en polvo", "protein": 80, "carbs": 5, "fat": 3,
                  "portion_unit": "g", "default_portion": 30, "household_amount": 1,
                  "household_measure": "scoop", "household_detail": ""},
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 200)
        food_id = created.json()["data"]["id"]
        self.assertEqual(created.json()["data"]["default_portion"], 30)
        self.assertEqual(created.json()["data"]["household_measure"], "scoop")
        picker = self.client.get(f"/api/v1/food-picker-options/{food_id}")
        self.assertEqual(picker.json()["data"]["household_measure_label"], "scoop")

        updated = self.client.put(
            f"/api/v1/library/foods/{food_id}/edit",
            data={"name": "Proteína en polvo", "protein": 80, "carbs": 5, "fat": 3,
                  "portion_unit": "g", "default_portion": 45, "household_amount": 2,
                  "household_measure": "other", "household_detail": "cacito"},
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["default_portion"], 45)
        self.assertEqual(FoodPortion.objects.filter(food_id=food_id, is_default=True).count(), 1)
        picker = self.client.get(f"/api/v1/food-picker-options/{food_id}")
        self.assertEqual(picker.json()["data"]["household_measure_label"], "cacito")
        self.assertEqual(picker.json()["data"]["household_amount"], 2)

    def test_personal_food_rejects_incomplete_equivalence(self):
        response = self.client.post(
            "/api/v1/library/foods",
            data={"name": "Yogur", "protein": 4, "carbs": 5, "fat": 2,
                  "default_portion": 150, "household_measure": "cup"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(Food.objects.filter(name="Yogur", created_by=self.user).exists())

    def test_food_detail_exposes_household_and_metric_portion_contract(self):
        food = Food.objects.create(
            name="Arroz personal",
            protein=7,
            carbs=78,
            fat=1,
            created_by=self.user,
            myscoope_group="cereals_and_pseudocereals",
            default_portion_g=150,
        )
        FoodPortion.objects.create(
            food=food,
            label="1 taza",
            grams=150,
            household_amount=1,
            household_measure="cup",
            household_detail="cocido",
            is_default=True,
        )

        response = self.client.get(f"/api/v1/food-picker-options/{food.id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(
            {
                key: payload[key]
                for key in (
                    "default_portion",
                    "household_amount",
                    "household_measure",
                    "household_measure_label",
                    "household_detail",
                    "myscoope_group_label",
                )
            },
            {
                "default_portion": 150.0,
                "household_amount": 1.0,
                "household_measure": "cup",
                "household_measure_label": "taza",
                "household_detail": "cocido",
                "myscoope_group_label": "Cereales y pseudocereales",
            },
        )
