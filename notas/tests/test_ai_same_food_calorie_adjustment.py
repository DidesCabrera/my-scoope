from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.ai_tools.proposal_tools import (
    create_proportional_dailyplan_calorie_proposal_tool,
)
from notas.application.services.commands.dailyplan_commands import (
    add_existing_meal_to_dailyplan,
)
from notas.application.services.commands.proposal_commands import (
    apply_approved_proposal,
    approve_proposal,
)
from notas.domain.models import DailyPlan, Food, Meal, MealFood, NutritionProposal


class AISameFoodCalorieAdjustmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass123")
        self.other_user = User.objects.create_user(username="other", password="pass123")
        self.food = Food.objects.create(
            name="Avena",
            protein=10,
            carbs=20,
            fat=0,
            created_by=self.user,
        )
        self.library_meal = Meal.objects.create(
            name="Desayuno de biblioteca",
            created_by=self.user,
            is_draft=False,
        )
        self.library_meal_food = MealFood.objects.create(
            meal=self.library_meal,
            food=self.food,
            quantity=100,
            order=1,
        )
        self.dailyplan = DailyPlan.objects.create(
            name="Plan X",
            created_by=self.user,
            is_draft=False,
        )
        add_result = add_existing_meal_to_dailyplan(
            dailyplan=self.dailyplan,
            meal=self.library_meal,
            user=self.user,
        )
        self.plan_meal = add_result.meal
        self.plan_meal_food = self.plan_meal.meal_food_set.get()

    def test_prepares_and_applies_plus_200_kcal_without_changing_library_meal(self):
        original_total = float(self.dailyplan.total_kcal)

        tool_result = create_proportional_dailyplan_calorie_proposal_tool(
            self.user,
            dailyplan_id=self.dailyplan.id,
            calorie_delta=200,
        )

        self.assertTrue(tool_result.ok)
        proposal = NutritionProposal.objects.get(
            pk=tool_result.data["proposal"]["id"],
        )
        payload = proposal.proposed_payload
        self.assertEqual(payload["strategy"], "proportional_quantity_scaling")
        self.assertTrue(payload["preserve_foods"])
        self.assertEqual(len(payload["suggested_changes"]), 1)
        self.assertEqual(
            payload["suggested_changes"][0]["mealfood_id"],
            self.plan_meal_food.id,
        )
        self.assertEqual(proposal.status, NutritionProposal.STATUS_PENDING_REVIEW)

        # Proposal preparation itself is non-destructive.
        self.plan_meal_food.refresh_from_db()
        self.assertEqual(self.plan_meal_food.quantity, 100)

        approve_proposal(user=self.user, proposal=proposal)
        apply_approved_proposal(user=self.user, proposal=proposal)

        self.library_meal_food.refresh_from_db()
        self.plan_meal_food.refresh_from_db()
        self.dailyplan.refresh_from_db()
        self.assertEqual(self.library_meal_food.quantity, 100)
        self.assertNotEqual(self.plan_meal_food.quantity, 100)
        self.assertAlmostEqual(
            float(self.dailyplan.total_kcal),
            original_total + 200,
            places=2,
        )

    def test_blocks_adjusting_another_users_plan(self):
        self.dailyplan.created_by = self.other_user
        self.dailyplan.save(update_fields=["created_by"])

        result = create_proportional_dailyplan_calorie_proposal_tool(
            self.user,
            dailyplan_id=self.dailyplan.id,
            calorie_delta=200,
        )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.error.code,
            "dailyplan_not_available_for_proposal",
        )

    def test_rejects_zero_delta_and_empty_plan(self):
        zero = create_proportional_dailyplan_calorie_proposal_tool(
            self.user,
            dailyplan_id=self.dailyplan.id,
            calorie_delta=0,
        )
        empty_plan = DailyPlan.objects.create(
            name="Sin alimentos",
            created_by=self.user,
            is_draft=True,
        )
        empty = create_proportional_dailyplan_calorie_proposal_tool(
            self.user,
            dailyplan_id=empty_plan.id,
            calorie_delta=200,
        )

        self.assertFalse(zero.ok)
        self.assertEqual(zero.error.code, "calorie_delta_must_not_be_zero")
        self.assertFalse(empty.ok)
        self.assertEqual(empty.error.code, "dailyplan_has_no_scalable_calories")
