import json
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    Meal,
    MealFood,
    NutritionProposal,
    WeightLog,
)


def json_post(client, url_name: str, payload: dict | None = None):
    return client.post(
        reverse(url_name),
        data=json.dumps(payload or {}),
        content_type="application/json",
    )


class AIToolsAPIContractTests(TestCase):
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

        for user in (self.user, self.other_user):
            profile = user.profile
            profile.onboarding_completed_at = timezone.now()
            profile.onboarding_version = profile.ONBOARDING_VERSION_NUTRITION_V1
            profile.save(update_fields=["onboarding_completed_at", "onboarding_version"])

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

        self.mealfood = MealFood.objects.create(
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

        self.proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Existing AI Proposal",
            summary="Existing proposal summary.",
            targets={
                "protein": 30,
            },
            current_snapshot={
                "dailyplan_id": self.dailyplan.id,
                "dailyplan_name": self.dailyplan.name,
                "actual": {
                    "protein": 10,
                },
            },
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [],
            },
            validation_summary={
                "within_tolerance": False,
            },
        )

    def assert_success_contract(self, response):
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

    def assert_error_contract(self, response, status_code: int = 200):
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
        self.assertEqual(
            set(data["error"].keys()),
            {
                "code",
                "message",
                "details",
            },
        )
        self.assertIsInstance(data["error"]["code"], str)
        self.assertIsInstance(data["error"]["message"], str)
        self.assertIsInstance(data["error"]["details"], dict)

        json.dumps(data)

        return data

    def test_successful_adapter_endpoints_follow_contract(self):
        self.client.force_login(self.user)

        calls = [
            (
                "ai_tools_health",
                {},
            ),
            (
                "ai_tools_read_food",
                {
                    "food_id": self.food.id,
                },
            ),
            (
                "ai_tools_read_meal",
                {
                    "meal_id": self.meal.id,
                },
            ),
            (
                "ai_tools_read_dailyplan",
                {
                    "dailyplan_id": self.dailyplan.id,
                },
            ),
            (
                "ai_tools_read_proposal",
                {
                    "proposal_id": self.proposal.id,
                },
            ),
            (
                "ai_tools_list_user_proposals",
                {},
            ),
            (
                "ai_tools_compare_dailyplan_to_targets",
                {
                    "dailyplan_id": self.dailyplan.id,
                    "targets": {
                        "protein": 30,
                    },
                },
            ),
            (
                "ai_tools_create_validated_dailyplan_proposal",
                {
                    "dailyplan_id": self.dailyplan.id,
                    "title": "Contract proposal",
                    "targets": {
                        "protein": 30,
                    },
                    "proposed_payload": {
                        "intent": "adjust_dailyplan_to_targets",
                        "suggested_changes": [],
                    },
                },
            ),
        ]

        for url_name, payload in calls:
            response = json_post(
                self.client,
                url_name,
                payload,
            )

            self.assert_success_contract(response)

    def test_error_adapter_endpoints_follow_contract(self):
        self.client.force_login(self.user)

        calls = [
            (
                "ai_tools_read_food",
                {},
                400,
            ),
            (
                "ai_tools_read_meal",
                {},
                400,
            ),
            (
                "ai_tools_read_dailyplan",
                {},
                400,
            ),
            (
                "ai_tools_read_proposal",
                {},
                400,
            ),
            (
                "ai_tools_compare_dailyplan_to_targets",
                {
                    "dailyplan_id": self.dailyplan.id,
                    "targets": {},
                },
                200,
            ),
            (
                "ai_tools_create_validated_dailyplan_proposal",
                {
                    "dailyplan_id": self.dailyplan.id,
                    "title": "Invalid proposal",
                    "targets": {},
                },
                200,
            ),
        ]

        for url_name, payload, status_code in calls:
            response = json_post(
                self.client,
                url_name,
                payload,
            )

            self.assert_error_contract(
                response,
                status_code=status_code,
            )

    def test_method_not_allowed_contract_is_stable_for_all_adapter_endpoints(self):
        self.client.force_login(self.user)

        endpoints = [
            "ai_tools_health",
            "ai_tools_read_food",
            "ai_tools_read_meal",
            "ai_tools_read_dailyplan",
            "ai_tools_read_proposal",
            "ai_tools_list_user_proposals",
            "ai_tools_compare_dailyplan_to_targets",
            "ai_tools_create_validated_dailyplan_proposal",
        ]

        for url_name in endpoints:
            response = self.client.get(
                reverse(url_name),
            )

            data = self.assert_error_contract(
                response,
                status_code=405,
            )

            self.assertEqual(
                data["error"]["code"],
                "method_not_allowed",
            )

    def test_invalid_json_contract_is_stable_for_all_adapter_endpoints(self):
        self.client.force_login(self.user)

        endpoints = [
            "ai_tools_health",
            "ai_tools_read_food",
            "ai_tools_read_meal",
            "ai_tools_read_dailyplan",
            "ai_tools_read_proposal",
            "ai_tools_list_user_proposals",
            "ai_tools_compare_dailyplan_to_targets",
            "ai_tools_create_validated_dailyplan_proposal",
        ]

        for url_name in endpoints:
            response = self.client.post(
                reverse(url_name),
                data="{invalid json",
                content_type="application/json",
            )

            data = self.assert_error_contract(
                response,
                status_code=400,
            )

            self.assertEqual(
                data["error"]["code"],
                "invalid_json",
            )

    def test_non_object_json_contract_is_stable_for_all_adapter_endpoints(self):
        self.client.force_login(self.user)

        endpoints = [
            "ai_tools_health",
            "ai_tools_read_food",
            "ai_tools_read_meal",
            "ai_tools_read_dailyplan",
            "ai_tools_read_proposal",
            "ai_tools_list_user_proposals",
            "ai_tools_compare_dailyplan_to_targets",
            "ai_tools_create_validated_dailyplan_proposal",
        ]

        for url_name in endpoints:
            response = self.client.post(
                reverse(url_name),
                data=json.dumps(["not", "an", "object"]),
                content_type="application/json",
            )

            data = self.assert_error_contract(
                response,
                status_code=400,
            )

            self.assertEqual(
                data["error"]["code"],
                "json_body_must_be_object",
            )

    def test_missing_required_field_contract_is_stable(self):
        self.client.force_login(self.user)

        checks = [
            (
                "ai_tools_read_food",
                "missing_required_field:food_id",
            ),
            (
                "ai_tools_read_meal",
                "missing_required_field:meal_id",
            ),
            (
                "ai_tools_read_dailyplan",
                "missing_required_field:dailyplan_id",
            ),
            (
                "ai_tools_read_proposal",
                "missing_required_field:proposal_id",
            ),
            (
                "ai_tools_compare_dailyplan_to_targets",
                "missing_required_field:dailyplan_id",
            ),
            (
                "ai_tools_create_validated_dailyplan_proposal",
                "missing_required_field:dailyplan_id",
            ),
        ]

        for url_name, expected_code in checks:
            response = json_post(
                self.client,
                url_name,
                {},
            )

            data = self.assert_error_contract(
                response,
                status_code=400,
            )

            self.assertEqual(
                data["error"]["code"],
                expected_code,
            )

    def test_success_payload_keys_are_stable(self):
        self.client.force_login(self.user)

        checks = [
            (
                "ai_tools_health",
                {},
                {
                    "status",
                    "adapter",
                },
            ),
            (
                "ai_tools_read_food",
                {
                    "food_id": self.food.id,
                },
                {
                    "food",
                },
            ),
            (
                "ai_tools_read_meal",
                {
                    "meal_id": self.meal.id,
                },
                {
                    "meal",
                },
            ),
            (
                "ai_tools_read_dailyplan",
                {
                    "dailyplan_id": self.dailyplan.id,
                },
                {
                    "dailyplan",
                },
            ),
            (
                "ai_tools_read_proposal",
                {
                    "proposal_id": self.proposal.id,
                },
                {
                    "proposal",
                },
            ),
            (
                "ai_tools_list_user_proposals",
                {},
                {
                    "proposals",
                },
            ),
            (
                "ai_tools_compare_dailyplan_to_targets",
                {
                    "dailyplan_id": self.dailyplan.id,
                    "targets": {
                        "protein": 30,
                    },
                },
                {
                    "validation",
                },
            ),
            (
                "ai_tools_create_validated_dailyplan_proposal",
                {
                    "dailyplan_id": self.dailyplan.id,
                    "title": "Stable payload proposal",
                    "targets": {
                        "protein": 30,
                    },
                },
                {
                    "proposal",
                },
            ),
        ]

        for url_name, payload, expected_keys in checks:
            response = json_post(
                self.client,
                url_name,
                payload,
            )

            data = self.assert_success_contract(response)

            self.assertEqual(
                set(data["data"].keys()),
                expected_keys,
            )

    def test_adapter_does_not_expose_apply_endpoint_contract(self):
        blocked_url_names = [
            "ai_tools_apply_approved_proposal",
            "ai_tools_apply_proposal",
            "ai_tools_apply_validated_proposal",
        ]

        for url_name in blocked_url_names:
            with self.assertRaises(NoReverseMatch):
                reverse(url_name)

    def test_adapter_login_redirects_are_not_json_contracts_by_design(self):
        response = json_post(
            self.client,
            "ai_tools_health",
            {},
        )

        self.assertEqual(response.status_code, 302)