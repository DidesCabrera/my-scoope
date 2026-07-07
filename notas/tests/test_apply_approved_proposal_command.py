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
)


class ApplyApprovedProposalCommandTests(TestCase):
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

    def test_apply_approved_proposal_updates_mealfood_and_marks_proposal_applied(self):
        result = apply_approved_proposal(
            user=self.user,
            proposal=self.proposal,
        )

        self.proposal.refresh_from_db()
        self.mealfood.refresh_from_db()

        self.assertEqual(
            result.proposal,
            self.proposal,
        )
        self.assertEqual(
            result.operations_result.applied_count,
            1,
        )

        self.assertEqual(
            self.mealfood.quantity,
            150,
        )

        self.assertEqual(
            self.proposal.status,
            NutritionProposal.STATUS_APPLIED,
        )
        self.assertEqual(
            self.proposal.applied_by,
            self.user,
        )
        self.assertIsNotNone(
            self.proposal.applied_at,
        )
        self.assertTrue(
            self.proposal.audit_events.filter(
                action="applied",
            ).exists()
        )

    def test_apply_approved_proposal_blocks_non_owner(self):
        with self.assertRaisesMessage(
            ValueError,
            "proposal_review_not_allowed",
        ):
            apply_approved_proposal(
                user=self.other_user,
                proposal=self.proposal,
            )

        self.mealfood.refresh_from_db()
        self.proposal.refresh_from_db()

        self.assertEqual(
            self.mealfood.quantity,
            100,
        )
        self.assertEqual(
            self.proposal.status,
            NutritionProposal.STATUS_APPROVED,
        )

    def test_apply_approved_proposal_requires_approved_status(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Pending proposal",
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            proposed_payload={
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

        with self.assertRaisesMessage(
            ValueError,
            "proposal_is_not_applicable",
        ):
            apply_approved_proposal(
                user=self.user,
                proposal=proposal,
            )

        self.mealfood.refresh_from_db()
        proposal.refresh_from_db()

        self.assertEqual(
            self.mealfood.quantity,
            100,
        )
        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_PENDING_REVIEW,
        )

    def test_apply_approved_proposal_blocks_double_application(self):
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

        self.mealfood.refresh_from_db()

        self.assertEqual(
            self.mealfood.quantity,
            150,
        )

    def test_apply_approved_proposal_reuses_validator_errors(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Invalid approved proposal",
            status=NutritionProposal.STATUS_APPROVED,
            proposed_payload={
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

        self.mealfood.refresh_from_db()
        proposal.refresh_from_db()

        self.assertEqual(
            self.mealfood.quantity,
            100,
        )
        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_APPROVED,
        )
        self.assertIsNone(
            proposal.applied_by,
        )
        self.assertIsNone(
            proposal.applied_at,
        )

    def test_apply_approved_proposal_allows_empty_payload_and_marks_applied(self):
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

        result = apply_approved_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()
        self.mealfood.refresh_from_db()

        self.assertEqual(
            result.operations_result.applied_count,
            0,
        )
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
            100,
        )