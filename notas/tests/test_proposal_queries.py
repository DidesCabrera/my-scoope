import json

from django.contrib.auth.models import User
from django.http import Http404
from django.test import TestCase

from notas.application.queries.proposal_queries import (
    get_proposal_detail,
    list_dailyplan_proposals,
    list_user_proposals,
    search_proposals,
)
from notas.domain.models import (
    DailyPlan,
    NutritionProposal,
)


def assert_json_serializable(test_case, value):
    try:
        json.dumps(value)
    except TypeError as exc:
        test_case.fail(f"Value is not JSON serializable: {exc}")


class ProposalQueryTests(TestCase):
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

        self.proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Increase protein",
            summary="Increase protein while keeping calories stable.",
            targets={
                "total_kcal": 2800,
                "protein": 190,
            },
            current_snapshot={
                "dailyplan_id": self.dailyplan.id,
                "total_kcal": 2600,
                "protein": 170,
            },
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [
                    {
                        "type": "update_meal_food_quantity",
                        "food_id": 1,
                        "from_quantity": 100,
                        "to_quantity": 150,
                    }
                ],
            },
            validation_summary={
                "within_tolerance": False,
            },
        )

        self.other_proposal = NutritionProposal.objects.create(
            dailyplan=self.other_dailyplan,
            created_by=self.other_user,
            title="Private other proposal",
            summary="This should not be visible.",
        )

    def test_list_user_proposals_returns_visible_proposals(self):
        proposals = list_user_proposals(self.user)

        data = [
            proposal.as_dict()
            for proposal in proposals
        ]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], self.proposal.id)
        self.assertEqual(data[0]["title"], "Increase protein")
        self.assertEqual(data[0]["dailyplan_id"], self.dailyplan.id)
        self.assertEqual(data[0]["dailyplan_name"], "Training Day")
        self.assertEqual(data[0]["status"], NutritionProposal.STATUS_PENDING_REVIEW)
        self.assertEqual(data[0]["source"], NutritionProposal.SOURCE_AI)
        self.assertTrue(data[0]["is_reviewable"])
        self.assertFalse(data[0]["is_final"])

        assert_json_serializable(self, data)

    def test_get_proposal_detail_returns_serializable_payload(self):
        dto = get_proposal_detail(
            self.user,
            self.proposal.id,
        )

        data = dto.as_dict()

        self.assertEqual(
            set(data.keys()),
            {
                "id",
                "dailyplan_id",
                "dailyplan_name",
                "created_by_id",
                "created_by_username",
                "reviewed_by_id",
                "reviewed_by_username",
                "status",
                "status_label",
                "source",
                "title",
                "summary",
                "targets",
                "current_snapshot",
                "proposed_payload",
                "validation_summary",
                "is_reviewable",
                "is_read",
                "is_final",
                "created_at",
                "received_at_label",
                "reviewed_at",
                "audit_events",
                "applied_at",
                "iteration_trace",
            },
        )

        self.assertEqual(data["id"], self.proposal.id)
        self.assertEqual(data["dailyplan_id"], self.dailyplan.id)
        self.assertEqual(data["created_by_id"], self.user.id)
        self.assertEqual(data["created_by_username"], "felipe")
        self.assertIsNone(data["reviewed_by_id"])
        self.assertIsNone(data["reviewed_by_username"])
        self.assertEqual(data["targets"]["protein"], 190)
        self.assertEqual(
            data["proposed_payload"]["intent"],
            "adjust_dailyplan_to_targets",
        )
        self.assertFalse(data["validation_summary"]["within_tolerance"])
        self.assertIsInstance(data["created_at"], str)
        self.assertIsNone(data["reviewed_at"])
        self.assertIsNone(data["iteration_trace"])

        assert_json_serializable(self, data)

    def test_get_proposal_detail_blocks_private_other_proposal(self):
        with self.assertRaises(Http404):
            get_proposal_detail(
                self.user,
                self.other_proposal.id,
            )

    def test_list_dailyplan_proposals_filters_by_dailyplan(self):
        proposals = list_dailyplan_proposals(
            self.user,
            self.dailyplan.id,
        )

        data = [
            proposal.as_dict()
            for proposal in proposals
        ]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], self.proposal.id)

        assert_json_serializable(self, data)

    def test_list_dailyplan_proposals_does_not_expose_other_dailyplan(self):
        proposals = list_dailyplan_proposals(
            self.user,
            self.other_dailyplan.id,
        )

        self.assertEqual(proposals, [])

    def test_search_proposals_matches_title_summary_and_dailyplan_name(self):
        by_title = search_proposals(
            self.user,
            "protein",
        )
        by_summary = search_proposals(
            self.user,
            "calories",
        )
        by_dailyplan = search_proposals(
            self.user,
            "training",
        )

        self.assertEqual(len(by_title), 1)
        self.assertEqual(len(by_summary), 1)
        self.assertEqual(len(by_dailyplan), 1)

        self.assertEqual(by_title[0].id, self.proposal.id)
        self.assertEqual(by_summary[0].id, self.proposal.id)
        self.assertEqual(by_dailyplan[0].id, self.proposal.id)

    def test_search_proposals_does_not_expose_private_other_proposal(self):
        proposals = search_proposals(
            self.user,
            "private other",
        )

        self.assertEqual(proposals, [])