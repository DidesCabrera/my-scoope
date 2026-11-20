import json
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.ai_tools.proposal_tools import (
    create_nutrition_engine_dailyplan_proposal_tool,
    create_validated_dailyplan_proposal_tool,
    list_dailyplan_proposals_tool,
    list_user_proposals_tool,
    read_proposal_tool,
    search_proposals_tool,
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


class AIProposalToolTests(TestCase):
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

    def assert_tool_success(self, result):
        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertIsInstance(data["data"], dict)
        self.assertIsNone(data["error"])

        assert_json_serializable(
            self,
            data,
        )

        return data

    def test_incomplete_nutrition_brief_reports_required_fields_without_creating_proposal(self):
        result = create_nutrition_engine_dailyplan_proposal_tool(
            self.user,
            nutrition_brief={"goal": "fat_loss", "weight_kg": 80, "height_cm": 175},
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "nutrition_brief_has_pending_questions")
        self.assertEqual(
            result.error.details["missing_fields"],
            ["age_years", "sex", "activity_level"],
        )
        self.assertEqual(NutritionProposal.objects.count(), 0)

    def assert_tool_error(self, result, code: str):
        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(data["data"], {})
        self.assertIsInstance(data["error"], dict)
        self.assertEqual(
            data["error"]["code"],
            code,
        )

        assert_json_serializable(
            self,
            data,
        )

        return data

    def test_create_validated_dailyplan_proposal_tool_creates_ai_proposal(self):
        result = create_validated_dailyplan_proposal_tool(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            title="AI protein adjustment",
            summary="Increase food quantity to move closer to protein target.",
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
        )

        data = self.assert_tool_success(result)

        proposal_data = data["data"]["proposal"]

        self.assertEqual(
            proposal_data["title"],
            "AI protein adjustment",
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

        self.assertTrue(
            proposal.audit_events.filter(
                action=NutritionProposalAuditEvent.ACTION_CREATED,
            ).exists()
        )

    def test_create_validated_dailyplan_proposal_tool_uses_default_payload(self):
        result = create_validated_dailyplan_proposal_tool(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            title="AI default payload proposal",
            targets={
                "protein": 30,
            },
        )

        data = self.assert_tool_success(result)

        proposal_data = data["data"]["proposal"]

        self.assertEqual(
            proposal_data["proposed_payload"],
            {
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [],
            },
        )

    def test_create_validated_dailyplan_proposal_tool_requires_title(self):
        result = create_validated_dailyplan_proposal_tool(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            title="   ",
            targets={
                "protein": 30,
            },
        )

        self.assert_tool_error(
            result,
            "tool_title_required",
        )

    def test_create_validated_dailyplan_proposal_tool_requires_targets_object(self):
        result = create_validated_dailyplan_proposal_tool(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            title="Invalid targets",
            targets=None,
        )

        self.assert_tool_error(
            result,
            "tool_targets_must_be_object",
        )

    def test_create_validated_dailyplan_proposal_tool_requires_non_empty_targets(self):
        result = create_validated_dailyplan_proposal_tool(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            title="Empty targets",
            targets={},
        )

        self.assert_tool_error(
            result,
            "tool_targets_required",
        )

    def test_create_validated_dailyplan_proposal_tool_rejects_invalid_payload(self):
        result = create_validated_dailyplan_proposal_tool(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            title="Invalid payload",
            targets={
                "protein": 30,
            },
            proposed_payload="invalid",
        )

        self.assert_tool_error(
            result,
            "tool_proposed_payload_must_be_object",
        )

    def test_create_validated_dailyplan_proposal_tool_blocks_other_dailyplan(self):
        result = create_validated_dailyplan_proposal_tool(
            user=self.user,
            dailyplan_id=self.other_dailyplan.id,
            title="Blocked proposal",
            targets={
                "protein": 30,
            },
        )

        self.assert_tool_error(
            result,
            "not_found",
        )

    def test_proposal_read_tools_return_created_proposal(self):
        created = create_validated_dailyplan_proposal_tool(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            title="Searchable AI proposal",
            summary="A searchable proposal summary.",
            targets={
                "protein": 30,
            },
        )

        created_data = self.assert_tool_success(created)
        proposal_id = created_data["data"]["proposal"]["id"]

        list_data = self.assert_tool_success(
            list_user_proposals_tool(self.user),
        )
        dailyplan_list_data = self.assert_tool_success(
            list_dailyplan_proposals_tool(
                self.user,
                self.dailyplan.id,
            ),
        )
        search_data = self.assert_tool_success(
            search_proposals_tool(
                self.user,
                "searchable",
            ),
        )
        detail_data = self.assert_tool_success(
            read_proposal_tool(
                self.user,
                proposal_id,
            ),
        )

        self.assertEqual(
            len(list_data["data"]["proposals"]),
            1,
        )
        self.assertEqual(
            len(dailyplan_list_data["data"]["proposals"]),
            1,
        )
        self.assertEqual(
            len(search_data["data"]["proposals"]),
            1,
        )
        self.assertEqual(
            detail_data["data"]["proposal"]["id"],
            proposal_id,
        )

    def test_read_proposal_tool_blocks_private_proposal(self):
        other_proposal = NutritionProposal.objects.create(
            dailyplan=self.other_dailyplan,
            created_by=self.other_user,
            title="Private other proposal",
        )

        result = read_proposal_tool(
            self.user,
            other_proposal.id,
        )

        self.assert_tool_error(
            result,
            "not_found",
        )
