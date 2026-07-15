from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.services.commands.proposal_commands import (
    apply_approved_proposal,
)
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    Meal,
    MealFood,
    NutritionProposal,
    NutritionProposalAuditEvent,
)


class ApplyProposalAuditTrailTests(TestCase):
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
            title="Approved quantity update",
            status=NutritionProposal.STATUS_APPROVED,
            proposed_payload={
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
        )

    def test_apply_approved_proposal_creates_applied_audit_event(self):
        result = apply_approved_proposal(
            user=self.user,
            proposal=self.proposal,
        )

        self.proposal.refresh_from_db()
        self.mealfood.refresh_from_db()

        event = self.proposal.audit_events.get(
            action=NutritionProposalAuditEvent.ACTION_APPLIED,
        )

        self.assertEqual(event.actor, self.user)
        self.assertEqual(
            event.status_before,
            NutritionProposal.STATUS_APPROVED,
        )
        self.assertEqual(
            event.status_after,
            NutritionProposal.STATUS_APPLIED,
        )
        self.assertEqual(
            event.message,
            "Nutrition proposal applied.",
        )

        self.assertEqual(
            event.metadata["proposal_id"],
            self.proposal.id,
        )
        self.assertEqual(
            event.metadata["applied_count"],
            1,
        )
        self.assertEqual(
            len(event.metadata["applied_operations"]),
            1,
        )

        operation = event.metadata["applied_operations"][0]

        self.assertEqual(
            operation["type"],
            "update_meal_food_quantity",
        )
        self.assertEqual(
            operation["mealfood_id"],
            self.mealfood.id,
        )
        self.assertEqual(
            operation["meal_id"],
            self.meal.id,
        )
        self.assertEqual(
            operation["food_id"],
            self.food.id,
        )
        self.assertEqual(
            operation["food_name"],
            "Base Food",
        )
        self.assertEqual(
            operation["quantity_before"],
            100,
        )
        self.assertEqual(
            operation["quantity_after"],
            150,
        )

        self.assertEqual(
            result.operations_result.applied_count,
            1,
        )
        self.assertEqual(
            self.mealfood.quantity,
            150,
        )

    def test_apply_empty_approved_proposal_creates_applied_audit_event(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Approved empty proposal",
            status=NutritionProposal.STATUS_APPROVED,
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [],
            },
        )

        apply_approved_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()

        event = proposal.audit_events.get(
            action=NutritionProposalAuditEvent.ACTION_APPLIED,
        )

        self.assertEqual(
            event.status_before,
            NutritionProposal.STATUS_APPROVED,
        )
        self.assertEqual(
            event.status_after,
            NutritionProposal.STATUS_APPLIED,
        )
        self.assertEqual(
            event.metadata["proposal_id"],
            proposal.id,
        )
        self.assertEqual(
            event.metadata["applied_count"],
            0,
        )
        self.assertEqual(
            event.metadata["applied_operations"],
            [],
        )

    def test_apply_invalid_proposal_does_not_create_applied_audit_event(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Invalid approved proposal",
            status=NutritionProposal.STATUS_APPROVED,
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [
                    {
                        "type": "update_meal_food_quantity",
                        "mealfood_id": self.mealfood.id,
                        "from_quantity": 80,
                        "to_quantity": 150,
                    }
                ],
            },
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_operation_from_quantity_mismatch",
        ):
            apply_approved_proposal(
                user=self.user,
                proposal=proposal,
            )

        proposal.refresh_from_db()
        self.mealfood.refresh_from_db()

        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_APPROVED,
        )
        self.assertEqual(
            self.mealfood.quantity,
            100,
        )
        self.assertFalse(
            proposal.audit_events.filter(
                action=NutritionProposalAuditEvent.ACTION_APPLIED,
            ).exists()
        )

    def test_apply_proposal_twice_does_not_create_second_applied_event(self):
        apply_approved_proposal(
            user=self.user,
            proposal=self.proposal,
        )

        self.proposal.refresh_from_db()

        with self.assertRaisesMessage(
            ValueError,
            "proposal_is_not_applicable",
        ):
            apply_approved_proposal(
                user=self.user,
                proposal=self.proposal,
            )

        self.assertEqual(
            self.proposal.audit_events.filter(
                action=NutritionProposalAuditEvent.ACTION_APPLIED,
            ).count(),
            1,
        )