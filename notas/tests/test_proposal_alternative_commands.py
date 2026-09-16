from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from notas.application.services.commands.proposal_alternative_commands import (
    select_proposal_alternative,
)
from notas.domain.models import Food, NutritionProposal


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class ProposalAlternativeCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="portfolio-owner")
        self.food_a = Food.objects.create(
            name="Food A",
            protein=20,
            carbs=10,
            fat=5,
            created_by=self.user,
        )
        self.food_b = Food.objects.create(
            name="Food B",
            protein=15,
            carbs=20,
            fat=4,
            created_by=self.user,
        )
        self.payload_a = self._payload("Plan A", self.food_a.id)
        self.payload_b = self._payload("Plan B", self.food_b.id)
        alternatives = [
            {"alternative_id": "alternative_1", "rank": 1, "payload": self.payload_a},
            {"alternative_id": "alternative_2", "rank": 2, "payload": self.payload_b},
        ]
        self.proposal = NutritionProposal.objects.create(
            created_by=self.user,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            source=NutritionProposal.SOURCE_AI,
            title="Portfolio",
            current_snapshot={
                "nutrition_solver": {
                    "alternatives": alternatives,
                    "selected_alternative_id": "alternative_1",
                }
            },
            proposed_payload=self.payload_a,
            validation_summary={},
        )

    @staticmethod
    def _payload(name, food_id):
        return {
            "intent": "create_dailyplan",
            "dailyplan": {
                "name": name,
                "meals": [
                    {
                        "hour": "12:00",
                        "note": "",
                        "meal": {
                            "name": f"{name} meal",
                            "foods": [{"food_id": food_id, "quantity": 100}],
                        },
                    }
                ],
            },
        }

    def test_selects_trusted_alternative_and_resimulates_proposal(self):
        selected = select_proposal_alternative(
            user=self.user,
            proposal=self.proposal,
            alternative_id="alternative_2",
        )

        self.assertEqual(selected.proposed_payload, self.payload_b)
        self.assertEqual(
            selected.current_snapshot["nutrition_solver"]["selected_alternative_id"],
            "alternative_2",
        )
        self.assertEqual(selected.validation_summary["selected_alternative_id"], "alternative_2")
        self.assertEqual(selected.validation_summary["simulation"]["dailyplan"]["name"], "Plan B")
        self.assertTrue(
            selected.audit_events.filter(
                metadata__event_type="solver_alternative_selected",
                metadata__alternative_id="alternative_2",
            ).exists()
        )

    def test_rejects_unknown_or_non_reviewable_alternative(self):
        with self.assertRaisesMessage(ValueError, "proposal_alternative_not_found"):
            select_proposal_alternative(
                user=self.user,
                proposal=self.proposal,
                alternative_id="missing",
            )

        self.proposal.status = NutritionProposal.STATUS_APPROVED
        self.proposal.save(update_fields=["status"])
        with self.assertRaisesMessage(ValueError, "proposal_alternative_not_reviewable"):
            select_proposal_alternative(
                user=self.user,
                proposal=self.proposal,
                alternative_id="alternative_2",
            )

    def test_trusted_web_action_selects_stored_alternative(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("proposal_select_alternative", args=[self.proposal.id]),
            {"alternative_id": "alternative_2"},
        )

        self.assertRedirects(response, reverse("proposal_detail", args=[self.proposal.id]))
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.proposed_payload, self.payload_b)
