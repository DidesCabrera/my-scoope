import json
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    Meal,
    MealFood,
    WeightLog,
)


def json_post(client, url_name: str, payload: dict | None = None):
    return client.post(
        reverse(url_name),
        data=json.dumps(payload or {}),
        content_type="application/json",
    )


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AIToolsAPIValidationEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@example.com",
            password="pass123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="pass123",
        )

        WeightLog.objects.create(
            user=self.user,
            date=date.today(),
            weight_kg=100,
        )

        self.food = Food.objects.create(
            name="Base Food",
            protein=10,
            carbs=20,
            fat=0,
            created_by=self.user,
        )

        self.meal = Meal.objects.create(
            name="Base Meal",
            created_by=self.user,
            is_public=False,
            is_draft=False,
        )

        MealFood.objects.create(
            meal=self.meal,
            food=self.food,
            quantity=100,
            order=1,
        )

        self.dailyplan = DailyPlan.objects.create(
            name="Training Day",
            created_by=self.user,
            is_public=False,
            is_draft=False,
        )

        DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=self.meal,
            order=1,
        )

        self.other_dailyplan = DailyPlan.objects.create(
            name="Private Other DailyPlan",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
        )

    def assert_success_response(self, response):
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(
            set(data.keys()),
            {
                "ok",
                "data",
                "error",
            },
        )
        self.assertTrue(data["ok"])
        self.assertIsInstance(data["data"], dict)
        self.assertIsNone(data["error"])

        json.dumps(data)

        return data

    def assert_error_response(self, response, code: str, status_code: int = 200):
        self.assertEqual(response.status_code, status_code)

        data = response.json()

        self.assertEqual(
            set(data.keys()),
            {
                "ok",
                "data",
                "error",
            },
        )
        self.assertFalse(data["ok"])
        self.assertEqual(data["data"], {})
        self.assertIsInstance(data["error"], dict)
        self.assertEqual(data["error"]["code"], code)

        json.dumps(data)

        return data

    def test_compare_endpoint_requires_login(self):
        response = json_post(
            self.client,
            "ai_tools_compare_dailyplan_to_targets",
            {
                "dailyplan_id": self.dailyplan.id,
                "targets": {
                    "protein": 30,
                },
            },
        )

        self.assertEqual(response.status_code, 302)

    def test_compare_endpoint_requires_post(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("ai_tools_compare_dailyplan_to_targets"),
        )

        self.assert_error_response(
            response,
            "method_not_allowed",
            status_code=405,
        )

    def test_compare_endpoint_returns_validation_summary(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_compare_dailyplan_to_targets",
            {
                "dailyplan_id": self.dailyplan.id,
                "targets": {
                    "total_kcal": 200,
                    "protein": 30,
                    "carbs": 20,
                    "fat": 0,
                    "ppk": 0.3,
                },
                "tolerances": {
                    "total_kcal": 10,
                    "protein": 5,
                    "carbs": 5,
                    "fat": 1,
                    "ppk": 0.05,
                },
            },
        )

        data = self.assert_success_response(response)

        validation = data["data"]["validation"]

        self.assertEqual(
            validation["dailyplan_id"],
            self.dailyplan.id,
        )
        self.assertEqual(
            validation["dailyplan_name"],
            "Training Day",
        )
        self.assertEqual(
            validation["actual"]["total_kcal"],
            120,
        )
        self.assertEqual(
            validation["actual"]["protein"],
            10,
        )
        self.assertEqual(
            validation["actual"]["carbs"],
            20,
        )
        self.assertEqual(
            validation["actual"]["fat"],
            0,
        )
        self.assertEqual(
            validation["actual"]["ppk"],
            0.1,
        )
        self.assertEqual(
            validation["delta"]["protein"],
            -20,
        )
        self.assertFalse(
            validation["within_tolerance"],
        )

    def test_compare_endpoint_uses_default_tolerances(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_compare_dailyplan_to_targets",
            {
                "dailyplan_id": self.dailyplan.id,
                "targets": {
                    "total_kcal": 200,
                },
            },
        )

        data = self.assert_success_response(response)

        validation = data["data"]["validation"]

        self.assertEqual(
            validation["tolerances"]["total_kcal"],
            100,
        )
        self.assertTrue(
            validation["within_tolerance"],
        )

    def test_compare_endpoint_requires_dailyplan_id(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_compare_dailyplan_to_targets",
            {
                "targets": {
                    "protein": 30,
                },
            },
        )

        self.assert_error_response(
            response,
            "missing_required_field:dailyplan_id",
            status_code=400,
        )

    def test_compare_endpoint_requires_targets(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_compare_dailyplan_to_targets",
            {
                "dailyplan_id": self.dailyplan.id,
            },
        )

        self.assert_error_response(
            response,
            "missing_required_field:targets",
            status_code=400,
        )

    def test_compare_endpoint_rejects_empty_targets(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_compare_dailyplan_to_targets",
            {
                "dailyplan_id": self.dailyplan.id,
                "targets": {},
            },
        )

        self.assert_error_response(
            response,
            "tool_targets_required",
        )

    def test_compare_endpoint_rejects_invalid_tolerances(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_compare_dailyplan_to_targets",
            {
                "dailyplan_id": self.dailyplan.id,
                "targets": {
                    "protein": 30,
                },
                "tolerances": "invalid",
            },
        )

        self.assert_error_response(
            response,
            "tool_tolerances_must_be_object",
        )

    def test_compare_endpoint_rejects_unknown_metric(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_compare_dailyplan_to_targets",
            {
                "dailyplan_id": self.dailyplan.id,
                "targets": {
                    "fiber": 30,
                },
            },
        )

        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(data["ok"])
        self.assertIn(
            "Unsupported target metrics",
            data["error"]["code"],
        )

    def test_compare_endpoint_blocks_private_dailyplan(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_compare_dailyplan_to_targets",
            {
                "dailyplan_id": self.other_dailyplan.id,
                "targets": {
                    "protein": 30,
                },
            },
        )

        self.assert_error_response(
            response,
            "not_found",
        )

    def test_compare_endpoint_rejects_invalid_json(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("ai_tools_compare_dailyplan_to_targets"),
            data="{invalid json",
            content_type="application/json",
        )

        self.assert_error_response(
            response,
            "invalid_json",
            status_code=400,
        )