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
    NutritionProposal,
    WeightLog,
)


def json_post(client, url_name: str, payload: dict | None = None):
    return client.post(
        reverse(url_name),
        data=json.dumps(payload or {}),
        content_type="application/json",
    )


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AIToolsAPIReadEndpointTests(TestCase):
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
        self.other_food = Food.objects.create(
            name="Private Other Food",
            protein=1,
            carbs=1,
            fat=1,
            created_by=self.other_user,
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

        self.other_meal = Meal.objects.create(
            name="Private Other Meal",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
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

        self.other_proposal = NutritionProposal.objects.create(
            dailyplan=self.other_dailyplan,
            created_by=self.other_user,
            title="Private Other Proposal",
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

    def test_read_endpoints_require_login(self):
        checks = [
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
        ]

        for url_name, payload in checks:
            response = json_post(
                self.client,
                url_name,
                payload,
            )

            self.assertEqual(response.status_code, 302)

    def test_read_food_endpoint_returns_food(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_read_food",
            {
                "food_id": self.food.id,
            },
        )

        data = self.assert_success_response(response)

        self.assertEqual(
            data["data"]["food"]["id"],
            self.food.id,
        )
        self.assertEqual(
            data["data"]["food"]["name"],
            "Base Food",
        )

    def test_read_meal_endpoint_returns_meal(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_read_meal",
            {
                "meal_id": self.meal.id,
            },
        )

        data = self.assert_success_response(response)

        self.assertEqual(
            data["data"]["meal"]["id"],
            self.meal.id,
        )
        self.assertEqual(
            data["data"]["meal"]["name"],
            "Base Meal",
        )

    def test_read_dailyplan_endpoint_returns_dailyplan(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_read_dailyplan",
            {
                "dailyplan_id": self.dailyplan.id,
            },
        )

        data = self.assert_success_response(response)

        self.assertEqual(
            data["data"]["dailyplan"]["id"],
            self.dailyplan.id,
        )
        self.assertEqual(
            data["data"]["dailyplan"]["name"],
            "Training Day",
        )

    def test_read_proposal_endpoint_returns_proposal(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_read_proposal",
            {
                "proposal_id": self.proposal.id,
            },
        )

        data = self.assert_success_response(response)

        self.assertEqual(
            data["data"]["proposal"]["id"],
            self.proposal.id,
        )
        self.assertEqual(
            data["data"]["proposal"]["title"],
            "Existing AI Proposal",
        )

    def test_list_user_proposals_endpoint_returns_proposals(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_list_user_proposals",
            {},
        )

        data = self.assert_success_response(response)

        self.assertEqual(
            len(data["data"]["proposals"]),
            1,
        )
        self.assertEqual(
            data["data"]["proposals"][0]["id"],
            self.proposal.id,
        )

    def test_read_endpoints_validate_required_fields(self):
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
        ]

        for url_name, error_code in checks:
            response = json_post(
                self.client,
                url_name,
                {},
            )

            self.assert_error_response(
                response,
                error_code,
                status_code=400,
            )

    def test_read_endpoints_block_private_resources(self):
        self.client.force_login(self.user)

        checks = [
            (
                "ai_tools_read_food",
                {
                    "food_id": self.other_food.id,
                },
            ),
            (
                "ai_tools_read_meal",
                {
                    "meal_id": self.other_meal.id,
                },
            ),
            (
                "ai_tools_read_dailyplan",
                {
                    "dailyplan_id": self.other_dailyplan.id,
                },
            ),
            (
                "ai_tools_read_proposal",
                {
                    "proposal_id": self.other_proposal.id,
                },
            ),
        ]

        for url_name, payload in checks:
            response = json_post(
                self.client,
                url_name,
                payload,
            )

            self.assert_error_response(
                response,
                "not_found",
            )

    def test_read_endpoints_require_post(self):
        self.client.force_login(self.user)

        endpoints = [
            "ai_tools_read_food",
            "ai_tools_read_meal",
            "ai_tools_read_dailyplan",
            "ai_tools_read_proposal",
            "ai_tools_list_user_proposals",
        ]

        for endpoint in endpoints:
            response = self.client.get(
                reverse(endpoint),
            )

            self.assert_error_response(
                response,
                "method_not_allowed",
                status_code=405,
            )