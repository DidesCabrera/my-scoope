from decimal import Decimal

from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from mobile_api.selectors import library_meals_payload
from mobile_api.tests.base import PaidMobileAPITestCase
from notas.domain.models import Food, Meal, MealFood, MealPreparation, Preparation, PreparationIngredient, PreparationVersion


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class LibraryProjectionPerformanceTests(PaidMobileAPITestCase):
    def test_mixed_meal_component_order_persists_across_projection_and_rejects_missing_rows(self):
        food = Food.objects.create(name="Avena", protein=13, carbs=68, fat=7, created_by=self.user)
        meal = Meal.objects.create(name="Comida mixta", created_by=self.user, is_draft=False)
        first = MealFood.objects.create(meal=meal, food=food, quantity=100, order=1)
        second = MealFood.objects.create(meal=meal, food=food, quantity=50, order=2)
        preparation = Preparation.objects.create(name="Avena preparada")
        version = PreparationVersion.objects.create(
            preparation=preparation, version=1, release_version="test", yield_g=Decimal("100"),
            default_portion_g=Decimal("50"), household_label="taza", protein_g=Decimal("13"),
            carbs_g=Decimal("68"), fat_g=Decimal("7"), sodium_mg=Decimal("0"),
            allergens=[], allergen_status="confirmed", ingredients_snapshot=[], content_sha256="test",
        )
        served = MealPreparation.objects.create(
            meal=meal, preparation=preparation, version=version, quantity_g=Decimal("50"),
            selected_units=Decimal("1"), selection_mode="units", order=3,
        )
        endpoint = f"/api/v1/library/meals/{meal.id}/components/order"
        keys = [f"meal-preparation:{served.id}", f"meal-food:{second.id}", f"meal-food:{first.id}"]
        invalid = self.client.put(endpoint, data={"ordered_keys": keys[:2]}, content_type="application/json")
        self.assertEqual(invalid.status_code, 422)
        result = self.client.put(endpoint, data={"ordered_keys": keys}, content_type="application/json")
        self.assertEqual(result.status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        served.refresh_from_db()
        self.assertEqual([served.order, second.order, first.order], [1, 2, 3])
        detail = self.client.get(f"/api/v1/library/meals/{meal.id}").json()["data"]["panel"]
        projected = [(row["order"], f"meal-food:{row['relation_id']}") for row in detail["foods"]]
        projected += [(row["order"], f"meal-preparation:{row['relation_id']}") for row in detail["preparations"]]
        self.assertEqual([key for _, key in sorted(projected)], keys)

    def test_meal_cards_have_a_constant_query_budget(self):
        food = Food.objects.create(name="Avena", protein=13, carbs=68, fat=7, created_by=self.user)
        for index in range(12):
            meal = Meal.objects.create(name=f"Comida {index}", created_by=self.user, is_draft=False)
            MealFood.objects.create(meal=meal, food=food, quantity=100)

        for limit in (1, 12):
            with self.subTest(limit=limit):
                with CaptureQueriesContext(connection) as queries:
                    payload = library_meals_payload(self.user, limit=limit, include_actions=False)

                self.assertEqual(len(payload["items"]), limit)
                self.assertEqual(payload["total"], 12)
                # The preparation relation adds one fixed prefetch, regardless of card count.
                self.assertLessEqual(len(queries), 7)

    def test_preparation_cards_keep_a_constant_query_budget(self):
        food = Food.objects.create(name="Avena", protein=13, carbs=68, fat=7, created_by=self.user)
        preparation = Preparation.objects.create(name="Avena preparada")
        version = PreparationVersion.objects.create(
            preparation=preparation, version=1, release_version="test", yield_g=Decimal("100"),
            default_portion_g=Decimal("50"), household_label="taza", protein_g=Decimal("13"),
            carbs_g=Decimal("68"), fat_g=Decimal("7"), sodium_mg=Decimal("0"),
            allergens=[], allergen_status="confirmed", ingredients_snapshot=[{
                "name": "Avena", "nutrition_per_100g": {
                    "protein_g": "13", "carbs_g": "68", "fat_g": "7", "sodium_mg": "0",
                },
            }],
            content_sha256="test",
        )
        preparation.current_version = version
        preparation.save(update_fields=["current_version"])
        PreparationIngredient.objects.create(version=version, food=food, quantity_g=Decimal("100"))
        for index in range(12):
            meal = Meal.objects.create(name=f"Comida {index}", created_by=self.user, is_draft=False)
            MealPreparation.objects.create(
                meal=meal, preparation=preparation, version=version, quantity_g=Decimal("50"),
                selected_units=Decimal("1"), selection_mode="units",
            )

        for limit in (1, 12):
            with self.subTest(limit=limit):
                with CaptureQueriesContext(connection) as queries:
                    payload = library_meals_payload(self.user, limit=limit, include_actions=False)
                self.assertEqual(len(payload["items"]), limit)
                self.assertEqual(len(payload["items"][0]["panel"]["preparations"]), 1)
                self.assertLessEqual(len(queries), 8)
