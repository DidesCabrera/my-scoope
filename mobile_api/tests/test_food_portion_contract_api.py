from django.test import override_settings

from mobile_api.tests.base import PaidMobileAPITestCase
from notas.domain.models import Food, FoodPortion


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class FoodPortionContractAPITests(PaidMobileAPITestCase):
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
