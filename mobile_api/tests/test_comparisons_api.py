from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.utils import timezone

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIComparisonTests(AuthenticatedMobileAPITestCase):
    def test_comparator_exposes_owned_options_and_authoritative_food_metrics(self):
        oats = Food.objects.create(
            name="Avena comparada",
            protein=10,
            carbs=20,
            fat=5,
            created_by=self.user,
        )
        rice = Food.objects.create(
            name="Arroz comparada",
            protein=3,
            carbs=28,
            fat=1,
            created_by=self.user,
        )
        other_user = User.objects.create_user(username="comparison-outsider")
        hidden = Food.objects.create(
            name="Alimento privado ajeno",
            protein=30,
            carbs=0,
            fat=2,
            created_by=other_user,
        )

        metadata = self.client.get("/api/v1/comparisons/metadata")
        options = self.client.get("/api/v1/comparisons/options/foods?search=comparada")
        compared = self.client.post(
            "/api/v1/comparisons/compare",
            data={
                "kind": "foods",
                "selections": [
                    {"id": oats.id, "quantity": 50},
                    {"id": rice.id, "quantity": 100},
                ],
            },
            content_type="application/json",
        )
        inaccessible = self.client.post(
            "/api/v1/comparisons/compare",
            data={
                "kind": "foods",
                "selections": [
                    {"id": oats.id, "quantity": 100},
                    {"id": hidden.id, "quantity": 100},
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(metadata.status_code, 200)
        self.assertEqual(
            [kind["key"] for kind in metadata.json()["data"]["kinds"]],
            ["foods", "meals", "dailyplans"],
        )
        self.assertNotIn("programs", [kind["key"] for kind in metadata.json()["data"]["kinds"]])
        self.assertEqual(options.status_code, 200)
        option_items = options.json()["data"]["items"]
        self.assertEqual({item["id"] for item in option_items}, {oats.id, rice.id})
        oats_option = next(item for item in option_items if item["id"] == oats.id)
        self.assertEqual(
            set(oats_option),
            {"id", "entity", "name", "subtitle", "nutrition", "indicators", "panel"},
        )
        self.assertEqual(oats_option["entity"], "food")
        self.assertEqual(oats_option["nutrition"]["calories"], 165.0)
        self.assertEqual(oats_option["nutrition"]["protein"]["grams"], 10.0)
        self.assertEqual(oats_option["indicators"], [{"icon": None, "label": "base nutricional", "value": "100 g"}])
        self.assertEqual(oats_option["panel"]["kind"], "none")
        self.assertEqual(compared.status_code, 200)
        first = compared.json()["data"]["items"][0]
        self.assertEqual(first["quantity"], 50.0)
        self.assertEqual(first["values"]["calories"], 82.5)
        self.assertEqual(first["values"]["protein_g"], 5.0)
        self.assertIsNone(first["values"]["protein_per_kilogram"])
        self.assertEqual(
            [metric["key"] for metric in compared.json()["data"]["metrics"]],
            ["total_kcal", "protein", "carbs", "fat", "alloc_protein", "alloc_carbs", "alloc_fat"],
        )
        calories = compared.json()["data"]["metrics"][0]
        self.assertEqual(calories["bars"][0]["formatted_value"], "82 kcal")
        self.assertEqual(calories["bars"][1]["relative_percentage"], 100.0)
        self.assertEqual(inaccessible.status_code, 404)
        self.assertEqual(inaccessible.json()["error"]["code"], "comparison_item_not_available")

        first_meal = Meal.objects.create(name="Comida uno", created_by=self.user, is_draft=False)
        second_meal = Meal.objects.create(name="Comida dos", created_by=self.user, is_draft=False)
        invalid_quantity = self.client.post(
            "/api/v1/comparisons/compare",
            data={
                "kind": "meals",
                "selections": [
                    {"id": first_meal.id, "quantity": 100},
                    {"id": second_meal.id},
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(invalid_quantity.status_code, 422)
        self.assertEqual(invalid_quantity.json()["error"]["code"], "comparison_quantity_not_allowed")

        repeated_food = self.client.post(
            "/api/v1/comparisons/compare",
            data={
                "kind": "foods",
                "selections": [{"id": oats.id}, {"id": oats.id, "quantity": 200}],
            },
            content_type="application/json",
        )
        self.assertEqual(repeated_food.status_code, 200)
        self.assertEqual([item["id"] for item in repeated_food.json()["data"]["items"]], [oats.id, oats.id])
        self.assertEqual([item["quantity"] for item in repeated_food.json()["data"]["items"]], [100.0, 200.0])
        self.assertEqual(
            [item["values"]["calories"] for item in repeated_food.json()["data"]["items"]],
            [165.0, 330.0],
        )
        self.assertEqual(
            [bar["relative_percentage"] for bar in repeated_food.json()["data"]["metrics"][0]["bars"]],
            [50.0, 100.0],
        )

    def test_comparator_options_deliver_complete_meal_and_dailyplan_cards(self):
        food = Food.objects.create(
            name="Ingrediente del selector",
            protein=10,
            carbs=20,
            fat=5,
            created_by=self.user,
        )
        meal = Meal.objects.create(
            name="Comida completa del selector",
            created_by=self.user,
            is_draft=False,
            protein_cached=10,
            carbs_cached=20,
            fat_cached=5,
            kcal_protein_cached=40,
            kcal_carbs_cached=80,
            kcal_fat_cached=45,
            total_kcal_cached=165,
            alloc_protein_cached=24.2,
            alloc_carbs_cached=48.5,
            alloc_fat_cached=27.3,
        )
        MealFood.objects.create(meal=meal, food=food, quantity=100)
        dailyplan = DailyPlan.objects.create(
            name="Plan completo del selector",
            created_by=self.user,
            is_draft=False,
            summary_cache={
                "totals": {
                    "protein": 10,
                    "carbs": 20,
                    "fat": 5,
                    "total_kcal": 165,
                    "alloc": {"protein": 24.2, "carbs": 48.5, "fat": 27.3},
                }
            },
        )
        embedded_meal = Meal.objects.create(
            name="Comida incluida en plan",
            created_by=self.user,
            is_draft=False,
            protein_cached=10,
            carbs_cached=20,
            fat_cached=5,
            kcal_protein_cached=40,
            kcal_carbs_cached=80,
            kcal_fat_cached=45,
            total_kcal_cached=165,
            alloc_protein_cached=24.2,
            alloc_carbs_cached=48.5,
            alloc_fat_cached=27.3,
        )
        MealFood.objects.create(meal=embedded_meal, food=food, quantity=100)
        DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=embedded_meal, hour="08:00")

        meal_response = self.client.get("/api/v1/comparisons/options/meals?search=Comida%20completa")
        dailyplan_response = self.client.get("/api/v1/comparisons/options/dailyplans?search=Plan%20completo")

        self.assertEqual(meal_response.status_code, 200)
        meal_option = meal_response.json()["data"]["items"][0]
        self.assertEqual(meal_option["entity"], "meal")
        self.assertEqual(meal_option["nutrition"]["calories"], 165.0)
        self.assertEqual(meal_option["indicators"][0], {"icon": "food", "label": "alimentos", "value": 1})
        self.assertEqual(meal_option["panel"]["kind"], "foods")
        self.assertEqual(meal_option["panel"]["foods"][0]["name"], "Ingrediente del selector")
        self.assertEqual(meal_option["panel"]["foods"][0]["quantity"], 100.0)

        self.assertEqual(dailyplan_response.status_code, 200)
        dailyplan_option = dailyplan_response.json()["data"]["items"][0]
        self.assertEqual(dailyplan_option["entity"], "dailyPlan")
        self.assertEqual(dailyplan_option["nutrition"]["calories"], 165.0)
        self.assertEqual(
            dailyplan_option["indicators"],
            [
                {"icon": "meal", "label": "comidas", "value": 1},
                {"icon": "food", "label": "alimentos", "value": 1},
            ],
        )
        self.assertEqual(dailyplan_option["panel"]["kind"], "meals")
        self.assertEqual(dailyplan_option["panel"]["meals"][0]["name"], "Comida incluida en plan")
        self.assertEqual(dailyplan_option["panel"]["meals"][0]["foods"][0]["name"], "Ingrediente del selector")

    def test_saved_comparison_is_owner_scoped_and_preserves_its_snapshot(self):
        first_food = Food.objects.create(
            name="Avena original",
            protein=10,
            carbs=20,
            fat=5,
            created_by=self.user,
        )
        second_food = Food.objects.create(
            name="Arroz original",
            protein=3,
            carbs=28,
            fat=1,
            created_by=self.user,
        )
        request_payload = {
            "kind": "foods",
            "selections": [
                {"id": first_food.id, "quantity": 100},
                {"id": second_food.id, "quantity": 100},
            ],
        }
        saved = self.client.post(
            "/api/v1/comparisons/saved",
            data=request_payload,
            content_type="application/json",
        )
        self.assertEqual(saved.status_code, 200)
        comparison_id = saved.json()["data"]["saved_comparison_id"]

        first_food.name = "Avena modificada"
        first_food.protein = 20
        first_food.save(update_fields=["name", "protein"])

        historical = self.client.get(f"/api/v1/comparisons/saved/{comparison_id}")
        self.assertEqual(historical.status_code, 200)
        self.assertTrue(historical.json()["data"]["historical_snapshot"])
        self.assertEqual(historical.json()["data"]["items"][0]["name"], "Avena original")
        self.assertEqual(historical.json()["data"]["items"][0]["values"]["protein_g"], 10.0)

        refreshed = self.client.put(
            f"/api/v1/comparisons/saved/{comparison_id}",
            data=request_payload,
            content_type="application/json",
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(refreshed.json()["data"]["items"][0]["name"], "Avena modificada")
        self.assertEqual(refreshed.json()["data"]["items"][0]["values"]["protein_g"], 20.0)

        other_user = User.objects.create_user(username="saved-comparison-outsider")
        other_token = create_mcp_user_token(
            user=other_user,
            name="Saved comparison outsider token",
            scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE],
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        outsider = Client(HTTP_AUTHORIZATION=f"Bearer {other_token.raw_token}")
        hidden = outsider.get(f"/api/v1/comparisons/saved/{comparison_id}")
        self.assertEqual(hidden.status_code, 404)
