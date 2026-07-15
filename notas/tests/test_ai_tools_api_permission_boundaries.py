import json
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse

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
class AIToolsAPIPermissionBoundaryTests(TestCase):
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

        WeightLog.objects.create(
            user=self.other_user,
            date=date.today(),
            weight_kg=80,
        )

        self.food = Food.objects.create(
            name="User Food",
            protein=10,
            carbs=20,
            fat=0,
            created_by=self.user,
        )
        self.other_food = Food.objects.create(
            name="Other Private Food",
            protein=1,
            carbs=1,
            fat=1,
            created_by=self.other_user,
        )

        self.meal = Meal.objects.create(
            name="User Meal",
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

        self.other_meal = Meal.objects.create(
            name="Other Private Meal",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
        )
        self.other_mealfood = MealFood.objects.create(
            meal=self.other_meal,
            food=self.other_food,
            quantity=100,
            order=1,
        )

        self.dailyplan = DailyPlan.objects.create(
            name="User DailyPlan",
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
            name="Other Private DailyPlan",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
        )
        DailyPlanMeal.objects.create(
            dailyplan=self.other_dailyplan,
            meal=self.other_meal,
            order=1,
        )

        self.proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="User Proposal",
            targets={
                "protein": 30,
            },
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [],
            },
        )

        self.other_proposal = NutritionProposal.objects.create(
            dailyplan=self.other_dailyplan,
            created_by=self.other_user,
            source=NutritionProposal.SOURCE_AI,
            title="Other Private Proposal",
            targets={
                "protein": 30,
            },
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [],
            },
        )

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

    def test_all_adapter_endpoints_require_login(self):
        endpoints = [
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
                    "title": "AI proposal",
                    "targets": {
                        "protein": 30,
                    },
                },
            ),
        ]

        for url_name, payload in endpoints:
            response = json_post(
                self.client,
                url_name,
                payload,
            )

            self.assertEqual(
                response.status_code,
                302,
                msg=f"{url_name} should require login.",
            )

    def test_all_adapter_endpoints_require_post(self):
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

            self.assert_error_response(
                response,
                "method_not_allowed",
                status_code=405,
            )

    def test_payload_user_id_cannot_override_request_user_for_read_dailyplan(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_read_dailyplan",
            {
                "user_id": self.other_user.id,
                "dailyplan_id": self.other_dailyplan.id,
            },
        )

        self.assert_error_response(
            response,
            "not_found",
        )

    def test_payload_user_id_cannot_override_request_user_for_read_food(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_read_food",
            {
                "user_id": self.other_user.id,
                "food_id": self.other_food.id,
            },
        )

        self.assert_error_response(
            response,
            "not_found",
        )

    def test_payload_user_id_cannot_override_request_user_for_read_meal(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_read_meal",
            {
                "user_id": self.other_user.id,
                "meal_id": self.other_meal.id,
            },
        )

        self.assert_error_response(
            response,
            "not_found",
        )

    def test_payload_user_id_cannot_override_request_user_for_read_proposal(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_read_proposal",
            {
                "user_id": self.other_user.id,
                "proposal_id": self.other_proposal.id,
            },
        )

        self.assert_error_response(
            response,
            "not_found",
        )

    def test_payload_user_id_cannot_override_request_user_for_validation(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_compare_dailyplan_to_targets",
            {
                "user_id": self.other_user.id,
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

    def test_payload_user_id_cannot_override_request_user_for_proposal_creation(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_proposal",
            {
                "user_id": self.other_user.id,
                "dailyplan_id": self.other_dailyplan.id,
                "title": "Should not be created",
                "targets": {
                    "protein": 30,
                },
            },
        )

        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(data["ok"])
        self.assertIn(
            data["error"]["code"],
            {
                "not_found",
                "dailyplan_not_available_for_proposal",
            },
        )

        self.assertFalse(
            NutritionProposal.objects.filter(
                dailyplan=self.other_dailyplan,
                created_by=self.user,
            ).exists()
        )

    def test_list_user_proposals_uses_request_user_only(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_list_user_proposals",
            {
                "user_id": self.other_user.id,
            },
        )

        data = self.assert_success_response(response)

        proposal_ids = [
            proposal["id"]
            for proposal in data["data"]["proposals"]
        ]

        self.assertIn(
            self.proposal.id,
            proposal_ids,
        )
        self.assertNotIn(
            self.other_proposal.id,
            proposal_ids,
        )

    def test_adapter_does_not_expose_apply_endpoint(self):
        blocked_url_names = [
            "ai_tools_apply_approved_proposal",
            "ai_tools_apply_proposal",
            "ai_tools_apply_validated_proposal",
        ]

        for url_name in blocked_url_names:
            with self.assertRaises(NoReverseMatch):
                reverse(url_name)

    def test_adapter_does_not_apply_payload_when_creating_proposal(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_proposal",
            {
                "dailyplan_id": self.dailyplan.id,
                "title": "Create only proposal",
                "targets": {
                    "protein": 30,
                },
                "proposed_payload": {
                    "intent": "adjust_dailyplan_to_targets",
                    "suggested_changes": [
                        {
                            "type": "update_meal_food_quantity",
                            "mealfood_id": self.mealfood.id,
                            "from_quantity": 100,
                            "to_quantity": 150,
                        }
                    ],
                },
            },
        )

        data = self.assert_success_response(response)

        proposal_id = data["data"]["proposal"]["id"]

        self.mealfood.refresh_from_db()

        self.assertEqual(
            self.mealfood.quantity,
            100,
        )

        proposal = NutritionProposal.objects.get(
            id=proposal_id,
        )

        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_PENDING_REVIEW,
        )