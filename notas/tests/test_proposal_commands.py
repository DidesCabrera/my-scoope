from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.services.commands.proposal_commands import (
    approve_proposal,
    cancel_proposal,
    create_dailyplan_proposal,
    reject_proposal,
    submit_proposal_for_review,
)

from notas.domain.models import (
    DailyPlan,
    NutritionProposal,
)


class ProposalCommandTests(TestCase):
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

        self.dailyplan = DailyPlan.objects.create(
            name="Training Day",
            created_by=self.user,
            is_public=False,
            is_draft=False,
        )
        self.other_dailyplan = DailyPlan.objects.create(
            name="Other Training Day",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
        )

    def test_create_dailyplan_proposal_for_owned_dailyplan(self):
        result = create_dailyplan_proposal(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            title="Increase protein",
            summary="Increase protein while keeping calories stable.",
            source=NutritionProposal.SOURCE_AI,
            targets={
                "protein": 190,
            },
            current_snapshot={
                "protein": 170,
            },
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [],
            },
            validation_summary={
                "within_tolerance": False,
            },
        )

        proposal = result.proposal

        self.assertEqual(proposal.dailyplan, self.dailyplan)
        self.assertEqual(proposal.created_by, self.user)
        self.assertEqual(proposal.title, "Increase protein")
        self.assertEqual(
            proposal.summary,
            "Increase protein while keeping calories stable.",
        )
        self.assertEqual(proposal.source, NutritionProposal.SOURCE_AI)
        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_PENDING_REVIEW,
        )
        self.assertEqual(proposal.targets["protein"], 190)
        self.assertEqual(
            proposal.proposed_payload["intent"],
            "adjust_dailyplan_to_targets",
        )
        self.assertTrue(proposal.is_reviewable)
        self.assertFalse(proposal.is_final)

    def test_create_dailyplan_proposal_can_create_draft(self):
        result = create_dailyplan_proposal(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            title="Draft proposal",
            status=NutritionProposal.STATUS_DRAFT,
        )

        proposal = result.proposal

        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_DRAFT,
        )
        self.assertFalse(proposal.is_reviewable)
        self.assertFalse(proposal.is_final)

    def test_create_dailyplan_proposal_requires_title(self):
        with self.assertRaisesMessage(
            ValueError,
            "proposal_title_required",
        ):
            create_dailyplan_proposal(
                user=self.user,
                dailyplan_id=self.dailyplan.id,
                title="   ",
            )

    def test_create_dailyplan_proposal_rejects_invalid_source(self):
        with self.assertRaisesMessage(
            ValueError,
            "invalid_proposal_source",
        ):
            create_dailyplan_proposal(
                user=self.user,
                dailyplan_id=self.dailyplan.id,
                title="Invalid source",
                source="robot",
            )

    def test_create_dailyplan_proposal_rejects_invalid_initial_status(self):
        with self.assertRaisesMessage(
            ValueError,
            "invalid_proposal_initial_status",
        ):
            create_dailyplan_proposal(
                user=self.user,
                dailyplan_id=self.dailyplan.id,
                title="Invalid status",
                status=NutritionProposal.STATUS_APPROVED,
            )

    def test_create_dailyplan_proposal_blocks_other_user_dailyplan(self):
        with self.assertRaisesMessage(
            ValueError,
            "dailyplan_not_available_for_proposal",
        ):
            create_dailyplan_proposal(
                user=self.user,
                dailyplan_id=self.other_dailyplan.id,
                title="Should not be created",
            )

    def test_submit_proposal_for_review_moves_draft_to_pending_review(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Draft proposal",
            status=NutritionProposal.STATUS_DRAFT,
        )

        result = submit_proposal_for_review(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()

        self.assertEqual(result.proposal, proposal)
        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_PENDING_REVIEW,
        )
        self.assertTrue(proposal.is_reviewable)

    def test_submit_proposal_for_review_blocks_other_user(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Draft proposal",
            status=NutritionProposal.STATUS_DRAFT,
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_submit_not_allowed",
        ):
            submit_proposal_for_review(
                user=self.other_user,
                proposal=proposal,
            )

    def test_submit_proposal_for_review_requires_draft(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Pending proposal",
            status=NutritionProposal.STATUS_PENDING_REVIEW,
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_is_not_draft",
        ):
            submit_proposal_for_review(
                user=self.user,
                proposal=proposal,
            )

    def test_cancel_proposal_marks_proposal_as_cancelled(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Proposal to cancel",
            status=NutritionProposal.STATUS_PENDING_REVIEW,
        )

        result = cancel_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()

        self.assertEqual(result.proposal, proposal)
        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_CANCELLED,
        )
        self.assertEqual(proposal.reviewed_by, self.user)
        self.assertIsNotNone(proposal.reviewed_at)
        self.assertTrue(proposal.is_final)

    def test_cancel_proposal_blocks_unrelated_user(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Proposal to cancel",
            status=NutritionProposal.STATUS_PENDING_REVIEW,
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_cancel_not_allowed",
        ):
            cancel_proposal(
                user=self.other_user,
                proposal=proposal,
            )

    def test_cancel_proposal_blocks_final_proposal(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Already rejected",
            status=NutritionProposal.STATUS_REJECTED,
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_is_final",
        ):
            cancel_proposal(
                user=self.user,
                proposal=proposal,
            )

    def test_reject_proposal_marks_proposal_as_rejected(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Proposal to reject",
            status=NutritionProposal.STATUS_PENDING_REVIEW,
        )

        result = reject_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()

        self.assertEqual(result.proposal, proposal)
        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_REJECTED,
        )
        self.assertEqual(proposal.reviewed_by, self.user)
        self.assertIsNotNone(proposal.reviewed_at)
        self.assertTrue(proposal.is_final)

    def test_reject_proposal_blocks_non_owner(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Proposal to reject",
            status=NutritionProposal.STATUS_PENDING_REVIEW,
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_review_not_allowed",
        ):
            reject_proposal(
                user=self.other_user,
                proposal=proposal,
            )

    def test_reject_proposal_requires_pending_review(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Draft proposal",
            status=NutritionProposal.STATUS_DRAFT,
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_is_not_pending_review",
        ):
            reject_proposal(
                user=self.user,
                proposal=proposal,
            )

    def test_approve_proposal_marks_proposal_as_approved_without_applying_payload(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Proposal to approve",
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [
                    {
                        "type": "update_meal_food_quantity",
                        "food_id": 123,
                        "from_quantity": 100,
                        "to_quantity": 150,
                    }
                ],
            },
        )

        result = approve_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()
        self.dailyplan.refresh_from_db()

        self.assertEqual(result.proposal, proposal)
        self.assertEqual(
            proposal.status,
            NutritionProposal.STATUS_APPROVED,
        )
        self.assertEqual(proposal.reviewed_by, self.user)
        self.assertIsNotNone(proposal.reviewed_at)
        self.assertFalse(proposal.is_final)

        # Importante: por ahora aprobar solo cambia el estado de la propuesta.
        # La aplicación real del proposed_payload vendrá en una etapa posterior.
        self.assertEqual(self.dailyplan.name, "Training Day")

    def test_approve_proposal_blocks_non_owner(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Proposal to approve",
            status=NutritionProposal.STATUS_PENDING_REVIEW,
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_review_not_allowed",
        ):
            approve_proposal(
                user=self.other_user,
                proposal=proposal,
            )

    def test_approve_proposal_requires_pending_review(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            title="Draft proposal",
            status=NutritionProposal.STATUS_DRAFT,
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_is_not_pending_review",
        ):
            approve_proposal(
                user=self.user,
                proposal=proposal,
            )