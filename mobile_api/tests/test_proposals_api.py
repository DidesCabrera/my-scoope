from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.utils import timezone

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE
from notas.domain.models import DailyPlan, Food, Meal, NutritionProposal


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIProposalTests(AuthenticatedMobileAPITestCase):
    def test_proposal_center_lists_details_and_separates_approval_from_application(self):
        food = Food.objects.create(
            name="Avena para propuesta",
            protein=13,
            carbs=68,
            fat=7,
            created_by=self.user,
        )
        context = DailyPlan.objects.create(
            name="Contexto de propuesta",
            created_by=self.user,
            is_draft=False,
        )
        proposal = NutritionProposal.objects.create(
            dailyplan=context,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            title="Desayuno propuesto",
            summary="Una comida revisable creada por AI.",
            targets={"protein": 30, "total_kcal": 500},
            current_snapshot={"dailyplan_id": context.id, "context": "meal_proposal"},
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Desayuno AI",
                    "foods": [{"food_id": food.id, "quantity": 100, "unit": "g"}],
                },
            },
            validation_summary={
                "payload_validation": {"is_valid": True, "intent": "create_meal"},
                "simulation": {
                    "intent": "create_meal",
                    "meal": {
                        "name": "Desayuno AI",
                        "foods": [{"food_id": food.id, "food_name": food.name, "quantity": 100, "unit": "g"}],
                        "kpis": {"protein": 13, "carbs": 68, "fat": 7, "total_kcal": 387},
                    },
                    "dailyplan": None,
                },
            },
        )

        proposal_list = self.client.get("/api/v1/proposals?status=pending_review")
        detail = self.client.get(f"/api/v1/proposals/{proposal.id}")
        approved = self.client.post(f"/api/v1/proposals/{proposal.id}/approve")

        self.assertEqual(proposal_list.status_code, 200)
        self.assertEqual(proposal_list.json()["data"]["pending_count"], 1)
        self.assertEqual(proposal_list.json()["data"]["items"][0]["id"], proposal.id)
        self.assertEqual(
            {action["key"] for action in detail.json()["data"]["actions"]}, {"approve", "reject", "cancel"}
        )
        self.assertEqual(detail.json()["data"]["meal"]["name"], "Desayuno AI")
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["data"]["status"], "approved")
        self.assertEqual(Meal.objects.filter(name="Desayuno AI").count(), 0)
        self.assertEqual([action["key"] for action in approved.json()["data"]["actions"]], ["apply", "cancel"])

        applied = self.client.post(
            f"/api/v1/proposals/{proposal.id}/apply",
            data={"acknowledge_external_subject": False},
            content_type="application/json",
        )
        replay = self.client.post(
            f"/api/v1/proposals/{proposal.id}/apply",
            data={"acknowledge_external_subject": False},
            content_type="application/json",
        )

        self.assertEqual(applied.status_code, 200)
        self.assertEqual(applied.json()["data"]["status"], "applied")
        self.assertEqual(applied.json()["data"]["applied_result"]["kind"], "meal")
        self.assertEqual(Meal.objects.filter(name="Desayuno AI").count(), 1)
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(Meal.objects.filter(name="Desayuno AI").count(), 1)

    def test_proposal_actions_require_ownership_and_external_subject_acknowledgement(self):
        food = Food.objects.create(name="Arroz AI", protein=3, carbs=28, fat=1, created_by=self.user)
        context = DailyPlan.objects.create(name="Contexto externo", created_by=self.user, is_draft=False)
        proposal = NutritionProposal.objects.create(
            dailyplan=context,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Comida para sujeto externo",
            targets={
                "subject_context": {
                    "source": "external_chat_data",
                    "requires_library_ppk_warning": True,
                    "calculation_weight_kg": 92,
                    "ppk_weight_source": "external_subject_weight",
                },
            },
            proposed_payload={
                "intent": "create_meal",
                "meal": {"name": "Comida externa", "foods": [{"food_id": food.id, "quantity": 100, "unit": "g"}]},
            },
        )

        warning = self.client.post(
            f"/api/v1/proposals/{proposal.id}/apply",
            data={"acknowledge_external_subject": False},
            content_type="application/json",
        )
        applied = self.client.post(
            f"/api/v1/proposals/{proposal.id}/apply",
            data={"acknowledge_external_subject": True},
            content_type="application/json",
        )

        other_user = User.objects.create_user(username="proposal-outsider")
        other_token = create_mcp_user_token(
            user=other_user,
            name="Proposal outsider token",
            scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE],
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        outsider = Client(HTTP_AUTHORIZATION=f"Bearer {other_token.raw_token}")
        hidden_detail = outsider.get(f"/api/v1/proposals/{proposal.id}")
        hidden_action = outsider.post(f"/api/v1/proposals/{proposal.id}/reject")

        self.assertEqual(warning.status_code, 409)
        self.assertEqual(warning.json()["error"]["code"], "proposal_external_subject_ack_required")
        self.assertEqual(applied.status_code, 200)
        self.assertEqual(applied.json()["data"]["status"], "applied")
        self.assertEqual(hidden_detail.status_code, 404)
        self.assertEqual(hidden_action.status_code, 404)
