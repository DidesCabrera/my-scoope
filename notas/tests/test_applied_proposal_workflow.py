import json
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.queries.proposal_queries import (
    get_proposal_detail,
)
from notas.application.services.commands.proposal_commands import (
    apply_approved_proposal,
    approve_proposal,
    create_validated_dailyplan_proposal,
)
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


def assert_json_serializable(test_case, value):
    try:
        json.dumps(value)
    except TypeError as exc:
        test_case.fail(f"Value is not JSON serializable: {exc}")


class AppliedProposalWorkflowTests(TestCase):
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

    def _create_validated_quantity_update_proposal(self):
        return create_validated_dailyplan_proposal(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            title="Apply protein adjustment",
            summary="Increase Base Food quantity from 100 to 150.",
            targets={
                "protein": 30,
                "total_kcal": 200,
            },
            tolerances={
                "protein": 5,
                "total_kcal": 10,
            },
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
        ).proposal

    def test_full_applied_proposal_workflow_updates_quantity_and_audit_trail(self):
        proposal = self._create_validated_quantity_update_proposal()

        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_PENDING_REVIEW,
        )

        self.assertEqual(
            proposal.audit_events.count(),
            1,
        )
        self.assertTrue(
            proposal.audit_events.filter(
                action=NutritionProposalAuditEvent.ACTION_CREATED,
            ).exists()
        )

        approve_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()

        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_APPROVED,
        )
        self.assertEqual(
            proposal.reviewed_by,
            self.user,
        )
        self.assertIsNotNone(
            proposal.reviewed_at,
        )

        self.assertTrue(
            proposal.audit_events.filter(
                action=NutritionProposalAuditEvent.ACTION_APPROVED,
            ).exists()
        )

        apply_result = apply_approved_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()
        self.mealfood.refresh_from_db()

        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_APPLIED,
        )
        self.assertEqual(
            proposal.applied_by,
            self.user,
        )
        self.assertIsNotNone(
            proposal.applied_at,
        )

        self.assertEqual(
            self.mealfood.quantity,
            150,
        )

        self.assertEqual(
            apply_result.operations_result.applied_count,
            1,
        )

        applied_operation = apply_result.operations_result.applied_operations[0]

        self.assertEqual(
            applied_operation.mealfood_id,
            self.mealfood.id,
        )
        self.assertEqual(
            applied_operation.quantity_before,
            100,
        )
        self.assertEqual(
            applied_operation.quantity_after,
            150,
        )

        self.assertEqual(
            proposal.audit_events.count(),
            3,
        )
        self.assertTrue(
            proposal.audit_events.filter(
                action=NutritionProposalAuditEvent.ACTION_CREATED,
            ).exists()
        )
        self.assertTrue(
            proposal.audit_events.filter(
                action=NutritionProposalAuditEvent.ACTION_APPROVED,
            ).exists()
        )
        self.assertTrue(
            proposal.audit_events.filter(
                action=NutritionProposalAuditEvent.ACTION_APPLIED,
            ).exists()
        )

        applied_event = proposal.audit_events.get(
            action=NutritionProposalAuditEvent.ACTION_APPLIED,
        )

        self.assertEqual(
            applied_event.status_before,
            NutritionProposal.STATUS_APPROVED,
        )
        self.assertEqual(
            applied_event.status_after,
            NutritionProposal.STATUS_APPLIED,
        )
        self.assertEqual(
            applied_event.metadata["applied_count"],
            1,
        )

        applied_event_operation = applied_event.metadata["applied_operations"][0]

        self.assertEqual(
            applied_event_operation["mealfood_id"],
            self.mealfood.id,
        )
        self.assertEqual(
            applied_event_operation["quantity_before"],
            100,
        )
        self.assertEqual(
            applied_event_operation["quantity_after"],
            150,
        )

        detail_data = get_proposal_detail(
            self.user,
            proposal.id,
        ).as_dict()

        self.assertEqual(
            detail_data["status"],
            NutritionProposal.STATUS_APPLIED,
        )
        self.assertTrue(
            detail_data["is_final"],
        )
        self.assertFalse(
            detail_data["is_reviewable"],
        )

        assert_json_serializable(
            self,
            detail_data,
        )
        assert_json_serializable(
            self,
            applied_event.metadata,
        )

    def test_full_applied_proposal_workflow_blocks_double_application(self):
        proposal = self._create_validated_quantity_update_proposal()

        approve_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()

        apply_approved_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()
        self.mealfood.refresh_from_db()

        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_APPLIED,
        )
        self.assertEqual(
            self.mealfood.quantity,
            150,
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_is_not_applicable",
        ):
            apply_approved_proposal(
                user=self.user,
                proposal=proposal,
            )

        proposal.refresh_from_db()
        self.mealfood.refresh_from_db()

        self.assertEqual(
            self.mealfood.quantity,
            150,
        )
        self.assertEqual(
            proposal.audit_events.filter(
                action=NutritionProposalAuditEvent.ACTION_APPLIED,
            ).count(),
            1,
        )

    def test_full_applied_proposal_workflow_blocks_unapproved_proposal(self):
        proposal = self._create_validated_quantity_update_proposal()

        with self.assertRaisesMessage(
            ValueError,
            "proposal_is_not_applicable",
        ):
            apply_approved_proposal(
                user=self.user,
                proposal=proposal,
            )

        proposal.refresh_from_db()
        self.mealfood.refresh_from_db()

        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_PENDING_REVIEW,
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

    def test_full_applied_proposal_workflow_blocks_unrelated_user(self):
        proposal = self._create_validated_quantity_update_proposal()

        approve_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()

        with self.assertRaisesMessage(
            ValueError,
            "proposal_review_not_allowed",
        ):
            apply_approved_proposal(
                user=self.other_user,
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

    def test_full_applied_proposal_workflow_blocks_stale_from_quantity(self):
        proposal = self._create_validated_quantity_update_proposal()

        approve_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()

        self.mealfood.quantity = 120
        self.mealfood.save(
            update_fields=[
                "quantity",
            ]
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
            120,
        )
        self.assertFalse(
            proposal.audit_events.filter(
                action=NutritionProposalAuditEvent.ACTION_APPLIED,
            ).exists()
        )
