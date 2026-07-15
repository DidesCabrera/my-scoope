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
    NutritionProposalAuditEvent,
    WeightLog,
)


def json_post(client, url_name: str, payload: dict | None = None):
    return client.post(
        reverse(url_name),
        data=json.dumps(payload or {}),
        content_type="application/json",
    )


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AIToolsAPIProposalEndpointTests(TestCase):
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

    def test_create_proposal_endpoint_requires_login(self):
        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_proposal",
            {
                "dailyplan_id": self.dailyplan.id,
                "title": "AI protein proposal",
                "targets": {
                    "protein": 30,
                },
            },
        )

        self.assertEqual(response.status_code, 302)

    def test_create_proposal_endpoint_requires_post(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("ai_tools_create_validated_dailyplan_proposal"),
        )

        self.assert_error_response(
            response,
            "method_not_allowed",
            status_code=405,
        )

    def test_create_proposal_endpoint_creates_validated_ai_proposal(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_proposal",
            {
                "dailyplan_id": self.dailyplan.id,
                "title": "AI protein proposal",
                "summary": "Increase Base Food quantity to move closer to protein target.",
                "targets": {
                    "protein": 30,
                    "total_kcal": 200,
                },
                "tolerances": {
                    "protein": 5,
                    "total_kcal": 10,
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

        proposal_data = data["data"]["proposal"]

        self.assertEqual(
            proposal_data["title"],
            "AI protein proposal",
        )
        self.assertEqual(
            proposal_data["dailyplan_id"],
            self.dailyplan.id,
        )
        self.assertEqual(
            proposal_data["source"],
            NutritionProposal.SOURCE_AI,
        )
        self.assertEqual(
            proposal_data["status"],
            NutritionProposal.STATUS_PENDING_REVIEW,
        )
        self.assertEqual(
            proposal_data["targets"]["protein"],
            30,
        )
        self.assertEqual(
            proposal_data["validation_summary"]["delta"]["protein"],
            -20,
        )
        self.assertEqual(
            proposal_data["proposed_payload"]["suggested_changes"][0]["to_quantity"],
            150,
        )

        proposal = NutritionProposal.objects.get(
            id=proposal_data["id"],
        )

        self.assertEqual(
            proposal.created_by,
            self.user,
        )
        self.assertEqual(
            proposal.dailyplan,
            self.dailyplan,
        )
        self.assertTrue(
            proposal.audit_events.filter(
                action=NutritionProposalAuditEvent.ACTION_CREATED,
            ).exists()
        )

        self.mealfood.refresh_from_db()

        # Importante:
        # el endpoint crea una propuesta, pero NO aplica cambios finales.
        self.assertEqual(
            self.mealfood.quantity,
            100,
        )

    def test_create_proposal_endpoint_uses_default_payload(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_proposal",
            {
                "dailyplan_id": self.dailyplan.id,
                "title": "Default payload proposal",
                "targets": {
                    "protein": 30,
                },
            },
        )

        data = self.assert_success_response(response)

        proposal_data = data["data"]["proposal"]

        self.assertEqual(
            proposal_data["proposed_payload"],
            {
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [],
            },
        )

    def test_create_proposal_endpoint_requires_dailyplan_id(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_proposal",
            {
                "title": "Missing dailyplan",
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

    def test_create_proposal_endpoint_requires_title(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_proposal",
            {
                "dailyplan_id": self.dailyplan.id,
                "targets": {
                    "protein": 30,
                },
            },
        )

        self.assert_error_response(
            response,
            "missing_required_field:title",
            status_code=400,
        )

    def test_create_proposal_endpoint_requires_targets(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_proposal",
            {
                "dailyplan_id": self.dailyplan.id,
                "title": "Missing targets",
            },
        )

        self.assert_error_response(
            response,
            "missing_required_field:targets",
            status_code=400,
        )

    def test_create_proposal_endpoint_rejects_blank_title(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_proposal",
            {
                "dailyplan_id": self.dailyplan.id,
                "title": "   ",
                "targets": {
                    "protein": 30,
                },
            },
        )

        self.assert_error_response(
            response,
            "tool_title_required",
        )

    def test_create_proposal_endpoint_rejects_empty_targets(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_proposal",
            {
                "dailyplan_id": self.dailyplan.id,
                "title": "Empty targets",
                "targets": {},
            },
        )

        self.assert_error_response(
            response,
            "tool_targets_required",
        )

    def test_create_proposal_endpoint_rejects_invalid_payload(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_proposal",
            {
                "dailyplan_id": self.dailyplan.id,
                "title": "Invalid payload",
                "targets": {
                    "protein": 30,
                },
                "proposed_payload": "invalid",
            },
        )

        self.assert_error_response(
            response,
            "tool_proposed_payload_must_be_object",
        )

    def test_create_proposal_endpoint_blocks_private_dailyplan(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_proposal",
            {
                "dailyplan_id": self.other_dailyplan.id,
                "title": "Blocked proposal",
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

        json.dumps(data)

    def test_create_proposal_endpoint_rejects_invalid_json(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("ai_tools_create_validated_dailyplan_proposal"),
            data="{invalid json",
            content_type="application/json",
        )

        self.assert_error_response(
            response,
            "invalid_json",
            status_code=400,
        )