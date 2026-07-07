from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.dto.proposal_apply import (
    build_create_dailyplan_apply_plan,
    build_create_meal_apply_plan,
)
from notas.domain.models import DailyPlan, NutritionProposal


class ProposalApplyDTOTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            password="pass123",
        )

        self.dailyplan = DailyPlan.objects.create(
            name="Training Day",
            created_by=self.user,
            is_public=False,
            is_draft=False,
        )

    def test_build_create_meal_apply_plan_returns_normalized_plan(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": 10,
                            "quantity": 200,
                        },
                        {
                            "food_id": 20,
                            "quantity": 150.5,
                            "unit": "g",
                        },
                    ],
                },
            },
        )

        apply_plan = build_create_meal_apply_plan(
            proposal=proposal,
        )

        self.assertEqual(
            apply_plan.as_dict(),
            {
                "proposal_id": proposal.id,
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": 10,
                            "quantity": 200.0,
                            "unit": "g",
                        },
                        {
                            "food_id": 20,
                            "quantity": 150.5,
                            "unit": "g",
                        },
                    ],
                },
            },
        )

    def test_build_create_meal_apply_plan_requires_approved_status(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": 10,
                            "quantity": 200,
                        },
                    ],
                },
            },
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_apply_requires_applicable_status",
        ):
            build_create_meal_apply_plan(
                proposal=proposal,
            )

    def test_build_create_meal_apply_plan_rejects_rejected_proposal(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_REJECTED,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": 10,
                            "quantity": 200,
                        },
                    ],
                },
            },
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_apply_requires_applicable_status",
        ):
            build_create_meal_apply_plan(
                proposal=proposal,
            )

    def test_build_create_meal_apply_plan_rejects_cancelled_proposal(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_CANCELLED,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": 10,
                            "quantity": 200,
                        },
                    ],
                },
            },
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_apply_requires_applicable_status",
        ):
            build_create_meal_apply_plan(
                proposal=proposal,
            )

    def test_build_create_meal_apply_plan_allows_approved_even_if_review_is_final(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": 10,
                            "quantity": 200,
                        },
                    ],
                },
            },
        )

        self.assertFalse(proposal.is_final)

        apply_plan = build_create_meal_apply_plan(
            proposal=proposal,
        )

        self.assertEqual(apply_plan.intent, "create_meal")

    def test_build_create_meal_apply_plan_rejects_dailyplan_payload(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Plan AI",
            proposed_payload={
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Día IA",
                    "meals": [
                        {
                            "meal": {
                                "name": "Meal",
                                "foods": [
                                    {
                                        "food_id": 10,
                                        "quantity": 100,
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_apply_intent_must_be_create_meal",
        ):
            build_create_meal_apply_plan(
                proposal=proposal,
            )

    def test_build_create_meal_apply_plan_rejects_invalid_payload(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Invalid",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Invalid",
                    "foods": [
                        {
                            "food_id": 10,
                            "quantity": 0,
                        },
                    ],
                },
            },
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposed_food_item_quantity_must_be_positive",
        ):
            build_create_meal_apply_plan(
                proposal=proposal,
            )

    def test_build_create_dailyplan_apply_plan_returns_normalized_plan(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Plan AI",
            proposed_payload={
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Día entrenamiento IA",
                    "meals": [
                        {
                            "hour": "9:05",
                            "note": "Desayuno",
                            "meal": {
                                "name": "Desayuno IA",
                                "foods": [
                                    {
                                        "food_id": 10,
                                        "quantity": 100,
                                    },
                                ],
                            },
                        },
                        {
                            "hour": "14:30",
                            "note": "",
                            "meal": {
                                "name": "Almuerzo IA",
                                "foods": [
                                    {
                                        "food_id": 20,
                                        "quantity": 200.5,
                                        "unit": "g",
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        )

        apply_plan = build_create_dailyplan_apply_plan(
            proposal=proposal,
        )

        self.assertEqual(
            apply_plan.as_dict(),
            {
                "proposal_id": proposal.id,
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Día entrenamiento IA",
                    "meals": [
                        {
                            "hour": "09:05",
                            "note": "Desayuno",
                            "meal": {
                                "name": "Desayuno IA",
                                "foods": [
                                    {
                                        "food_id": 10,
                                        "quantity": 100.0,
                                        "unit": "g",
                                    },
                                ],
                            },
                        },
                        {
                            "hour": "14:30",
                            "note": "",
                            "meal": {
                                "name": "Almuerzo IA",
                                "foods": [
                                    {
                                        "food_id": 20,
                                        "quantity": 200.5,
                                        "unit": "g",
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        )

    def test_build_create_dailyplan_apply_plan_requires_approved_status(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            title="Plan AI",
            proposed_payload={
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Día IA",
                    "meals": [
                        {
                            "meal": {
                                "name": "Meal",
                                "foods": [
                                    {
                                        "food_id": 10,
                                        "quantity": 100,
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_apply_requires_applicable_status",
        ):
            build_create_dailyplan_apply_plan(
                proposal=proposal,
            )

    def test_build_create_dailyplan_apply_plan_rejects_meal_payload(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": 10,
                            "quantity": 100,
                        },
                    ],
                },
            },
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_apply_intent_must_be_create_dailyplan",
        ):
            build_create_dailyplan_apply_plan(
                proposal=proposal,
            )

    def test_build_create_dailyplan_apply_plan_rejects_invalid_payload(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Invalid",
            proposed_payload={
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Invalid",
                    "meals": [
                        {
                            "hour": "25:00",
                            "meal": {
                                "name": "Meal",
                                "foods": [
                                    {
                                        "food_id": 10,
                                        "quantity": 100,
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposed_dailyplan_meal_hour_out_of_range",
        ):
            build_create_dailyplan_apply_plan(
                proposal=proposal,
            )