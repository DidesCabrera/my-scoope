import json
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.ai_tools.read_tools import (
    list_available_dailyplans_tool,
    list_available_foods_tool,
    list_available_meals_tool,
    list_dailyplan_proposals_tool,
    list_user_dailyplans_tool,
    list_user_foods_tool,
    list_user_meals_tool,
    list_user_proposals_tool,
    read_dailyplan_tool,
    read_food_tool,
    read_meal_tool,
    read_proposal_tool,
    search_dailyplans_tool,
    search_foods_tool,
    search_meals_tool,
    search_proposals_tool,
)
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    Meal,
    MealFood,
    NutritionProposal,
    WeightLog,
)


def assert_json_serializable(test_case, value):
    try:
        json.dumps(value)
    except TypeError as exc:
        test_case.fail(f"Value is not JSON serializable: {exc}")


class AIReadToolTests(TestCase):
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
        self.other_food = Food.objects.create(
            name="Private Other Food",
            protein=1,
            carbs=1,
            fat=1,
            created_by=self.other_user,
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

        self.other_meal = Meal.objects.create(
            name="Private Other Meal",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
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

        self.proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Increase protein",
            summary="Increase protein while keeping calories stable.",
            targets={
                "protein": 190,
            },
            current_snapshot={
                "dailyplan_id": self.dailyplan.id,
                "dailyplan_name": self.dailyplan.name,
                "actual": {
                    "protein": 170,
                },
            },
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [],
            },
            validation_summary={
                "within_tolerance": False,
            },
        )

        self.other_proposal = NutritionProposal.objects.create(
            dailyplan=self.other_dailyplan,
            created_by=self.other_user,
            title="Private Other Proposal",
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

    def test_food_read_tools_return_success_contracts(self):
        list_data = self.assert_tool_success(
            list_user_foods_tool(self.user),
        )
        available_data = self.assert_tool_success(
            list_available_foods_tool(self.user),
        )
        search_data = self.assert_tool_success(
            search_foods_tool(
                self.user,
                "base",
            ),
        )
        detail_data = self.assert_tool_success(
            read_food_tool(
                self.user,
                self.food.id,
            ),
        )

        self.assertEqual(
            len(list_data["data"]["foods"]),
            1,
        )
        self.assertGreaterEqual(
            len(available_data["data"]["foods"]),
            1,
        )
        self.assertEqual(
            search_data["data"]["query"],
            "base",
        )
        self.assertEqual(
            detail_data["data"]["food"]["id"],
            self.food.id,
        )

    def test_food_read_exposes_its_nutrition_base_unit(self):
        self.food.portion_unit = "ml"
        self.food.save(update_fields=["portion_unit"])

        data = self.assert_tool_success(read_food_tool(self.user, self.food.id))

        self.assertEqual(data["data"]["food"]["portion_unit"], "ml")

    def test_food_read_tool_blocks_private_other_food(self):
        result = read_food_tool(
            self.user,
            self.other_food.id,
        )

        self.assert_tool_error(
            result,
            "not_found",
        )

    def test_meal_read_tools_return_success_contracts(self):
        list_data = self.assert_tool_success(
            list_user_meals_tool(self.user),
        )
        available_data = self.assert_tool_success(
            list_available_meals_tool(self.user),
        )
        search_data = self.assert_tool_success(
            search_meals_tool(
                self.user,
                "base",
            ),
        )
        detail_data = self.assert_tool_success(
            read_meal_tool(
                self.user,
                self.meal.id,
            ),
        )

        self.assertEqual(
            len(list_data["data"]["meals"]),
            1,
        )
        self.assertGreaterEqual(
            len(available_data["data"]["meals"]),
            1,
        )
        self.assertEqual(
            search_data["data"]["query"],
            "base",
        )
        self.assertEqual(
            detail_data["data"]["meal"]["id"],
            self.meal.id,
        )

    def test_meal_read_tool_blocks_private_other_meal(self):
        result = read_meal_tool(
            self.user,
            self.other_meal.id,
        )

        self.assert_tool_error(
            result,
            "not_found",
        )

    def test_dailyplan_read_tools_return_success_contracts(self):
        list_data = self.assert_tool_success(
            list_user_dailyplans_tool(self.user),
        )
        available_data = self.assert_tool_success(
            list_available_dailyplans_tool(self.user),
        )
        search_data = self.assert_tool_success(
            search_dailyplans_tool(
                self.user,
                "training",
            ),
        )
        detail_data = self.assert_tool_success(
            read_dailyplan_tool(
                self.user,
                self.dailyplan.id,
            ),
        )

        self.assertEqual(
            len(list_data["data"]["dailyplans"]),
            1,
        )
        self.assertGreaterEqual(
            len(available_data["data"]["dailyplans"]),
            1,
        )
        self.assertEqual(
            search_data["data"]["query"],
            "training",
        )
        self.assertEqual(
            detail_data["data"]["dailyplan"]["id"],
            self.dailyplan.id,
        )

    def test_dailyplan_read_tool_blocks_private_other_dailyplan(self):
        result = read_dailyplan_tool(
            self.user,
            self.other_dailyplan.id,
        )

        self.assert_tool_error(
            result,
            "not_found",
        )

    def test_proposal_read_tools_return_success_contracts(self):
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
                "protein",
            ),
        )
        detail_data = self.assert_tool_success(
            read_proposal_tool(
                self.user,
                self.proposal.id,
            ),
        )

        self.assertEqual(
            len(list_data["data"]["proposals"]),
            1,
        )
        self.assertEqual(
            dailyplan_list_data["data"]["dailyplan_id"],
            self.dailyplan.id,
        )
        self.assertEqual(
            len(dailyplan_list_data["data"]["proposals"]),
            1,
        )
        self.assertEqual(
            search_data["data"]["query"],
            "protein",
        )
        self.assertEqual(
            detail_data["data"]["proposal"]["id"],
            self.proposal.id,
        )

    def test_proposal_read_tool_blocks_private_other_proposal(self):
        result = read_proposal_tool(
            self.user,
            self.other_proposal.id,
        )

        self.assert_tool_error(
            result,
            "not_found",
        )