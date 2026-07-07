from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.services.commands.proposal_commands import (
    apply_approved_create_dailyplan_proposal,
)
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    Meal,
    MealFood,
    NutritionProposal,
)


class ApplyCreateDailyPlanProposalCommandTests(TestCase):
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

        self.context_dailyplan = DailyPlan.objects.create(
            name="Context Training Day",
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

        self.chicken = Food.objects.create(
            name="Pechuga pollo",
            protein=31,
            carbs=0,
            fat=3.6,
            created_by=self.user,
        )
        self.rice = Food.objects.create(
            name="Arroz blanco",
            protein=2.7,
            carbs=28,
            fat=0.3,
            created_by=self.user,
        )
        self.system_banana = Food.objects.create(
            name="Plátano",
            protein=1.1,
            carbs=23,
            fat=0.3,
            created_by=None,
        )
        self.private_other_food = Food.objects.create(
            name="Private Other Food",
            protein=100,
            carbs=100,
            fat=100,
            created_by=self.other_user,
        )

    def _create_approved_create_dailyplan_proposal(
        self,
        *,
        source=NutritionProposal.SOURCE_AI,
        meals=None,
    ):
        return NutritionProposal.objects.create(
            dailyplan=self.context_dailyplan,
            created_by=self.user,
            source=source,
            status=NutritionProposal.STATUS_APPROVED,
            title="Plan AI",
            proposed_payload={
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Día entrenamiento IA",
                    "meals": meals or [
                        {
                            "hour": "09:00",
                            "note": "Desayuno",
                            "meal": {
                                "name": "Desayuno IA",
                                "foods": [
                                    {
                                        "food_id": self.rice.id,
                                        "quantity": 100,
                                        "unit": "g",
                                    },
                                ],
                            },
                        },
                        {
                            "hour": "14:30",
                            "note": "Almuerzo",
                            "meal": {
                                "name": "Almuerzo IA",
                                "foods": [
                                    {
                                        "food_id": self.chicken.id,
                                        "quantity": 200,
                                        "unit": "g",
                                    },
                                    {
                                        "food_id": self.system_banana.id,
                                        "quantity": 150,
                                        "unit": "g",
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        )

    def test_apply_approved_create_dailyplan_proposal_creates_real_dailyplan_with_snapshots(self):
        proposal = self._create_approved_create_dailyplan_proposal()

        before_dailyplan_count = DailyPlan.objects.count()
        before_meal_count = Meal.objects.count()
        before_mealfood_count = MealFood.objects.count()
        before_dpm_count = DailyPlanMeal.objects.count()

        result = apply_approved_create_dailyplan_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()

        self.assertEqual(DailyPlan.objects.count(), before_dailyplan_count + 1)
        self.assertEqual(Meal.objects.count(), before_meal_count + 2)
        self.assertEqual(MealFood.objects.count(), before_mealfood_count + 3)
        self.assertEqual(DailyPlanMeal.objects.count(), before_dpm_count + 2)

        dailyplan = result.dailyplan

        self.assertEqual(dailyplan.name, "Día entrenamiento IA")
        self.assertEqual(dailyplan.created_by, self.user)
        self.assertEqual(dailyplan.source, DailyPlan.SOURCE_AI)
        self.assertFalse(dailyplan.is_public)
        self.assertTrue(dailyplan.is_forkable)
        self.assertFalse(dailyplan.is_copiable)
        self.assertFalse(dailyplan.is_draft)
        self.assertIsNone(dailyplan.forked_from)
        self.assertIsNone(dailyplan.original_author)

        dailyplan_meals = list(
            dailyplan.dailyplan_meals
            .select_related("meal")
            .order_by("order", "id")
        )

        self.assertEqual(len(dailyplan_meals), 2)

        breakfast = dailyplan_meals[0]
        lunch = dailyplan_meals[1]

        self.assertEqual(breakfast.order, 1)
        self.assertEqual(breakfast.hour.strftime("%H:%M"), "09:00")
        self.assertEqual(breakfast.note, "Desayuno")
        self.assertEqual(breakfast.meal.name, "Desayuno IA")
        self.assertEqual(breakfast.meal.created_by, self.user)
        self.assertFalse(breakfast.meal.is_draft)
        self.assertIsNone(breakfast.meal.pending_dailyplan)

        self.assertEqual(lunch.order, 2)
        self.assertEqual(lunch.hour.strftime("%H:%M"), "14:30")
        self.assertEqual(lunch.note, "Almuerzo")
        self.assertEqual(lunch.meal.name, "Almuerzo IA")
        self.assertEqual(lunch.meal.created_by, self.user)
        self.assertFalse(lunch.meal.is_draft)
        self.assertIsNone(lunch.meal.pending_dailyplan)

        breakfast_foods = list(
            breakfast.meal.meal_food_set
            .select_related("food")
            .order_by("order", "id")
        )
        lunch_foods = list(
            lunch.meal.meal_food_set
            .select_related("food")
            .order_by("order", "id")
        )

        self.assertEqual(len(breakfast_foods), 1)
        self.assertEqual(breakfast_foods[0].food, self.rice)
        self.assertEqual(breakfast_foods[0].quantity, 100.0)
        self.assertEqual(breakfast_foods[0].order, 1)

        self.assertEqual(len(lunch_foods), 2)
        self.assertEqual(lunch_foods[0].food, self.chicken)
        self.assertEqual(lunch_foods[0].quantity, 200.0)
        self.assertEqual(lunch_foods[0].order, 1)
        self.assertEqual(lunch_foods[1].food, self.system_banana)
        self.assertEqual(lunch_foods[1].quantity, 150.0)
        self.assertEqual(lunch_foods[1].order, 2)

        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPLIED)
        self.assertEqual(proposal.applied_by, self.user)
        self.assertIsNotNone(proposal.applied_at)

    def test_apply_approved_create_dailyplan_proposal_preserves_mcp_source(self):
        proposal = self._create_approved_create_dailyplan_proposal(
            source=NutritionProposal.SOURCE_MCP,
        )

        result = apply_approved_create_dailyplan_proposal(
            user=self.user,
            proposal=proposal,
        )

        self.assertEqual(result.dailyplan.source, DailyPlan.SOURCE_MCP)

    def test_apply_approved_create_dailyplan_proposal_does_not_modify_context_dailyplan(self):
        proposal = self._create_approved_create_dailyplan_proposal()

        context_id = self.context_dailyplan.id
        context_name = self.context_dailyplan.name

        result = apply_approved_create_dailyplan_proposal(
            user=self.user,
            proposal=proposal,
        )

        self.context_dailyplan.refresh_from_db()

        self.assertEqual(self.context_dailyplan.id, context_id)
        self.assertEqual(self.context_dailyplan.name, context_name)
        self.assertNotEqual(result.dailyplan.id, self.context_dailyplan.id)

    def test_apply_approved_create_dailyplan_proposal_rejects_private_other_food(self):
        proposal = self._create_approved_create_dailyplan_proposal(
            meals=[
                {
                    "hour": "09:00",
                    "note": "Desayuno",
                    "meal": {
                        "name": "Invalid Meal",
                        "foods": [
                            {
                                "food_id": self.private_other_food.id,
                                "quantity": 100,
                                "unit": "g",
                            },
                        ],
                    },
                },
            ],
        )

        before_dailyplan_count = DailyPlan.objects.count()
        before_meal_count = Meal.objects.count()
        before_mealfood_count = MealFood.objects.count()
        before_dpm_count = DailyPlanMeal.objects.count()

        with self.assertRaisesMessage(
            ValueError,
            "proposal_apply_food_not_available",
        ):
            apply_approved_create_dailyplan_proposal(
                user=self.user,
                proposal=proposal,
            )

        proposal.refresh_from_db()

        self.assertEqual(DailyPlan.objects.count(), before_dailyplan_count)
        self.assertEqual(Meal.objects.count(), before_meal_count)
        self.assertEqual(MealFood.objects.count(), before_mealfood_count)
        self.assertEqual(DailyPlanMeal.objects.count(), before_dpm_count)
        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPROVED)
        self.assertIsNone(proposal.applied_by)
        self.assertIsNone(proposal.applied_at)

    def test_apply_approved_create_dailyplan_proposal_requires_owner(self):
        proposal = self._create_approved_create_dailyplan_proposal()

        with self.assertRaisesMessage(
            ValueError,
            "proposal_review_not_allowed",
        ):
            apply_approved_create_dailyplan_proposal(
                user=self.other_user,
                proposal=proposal,
            )

        proposal.refresh_from_db()

        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPROVED)
        self.assertEqual(DailyPlan.objects.count(), 2)

    def test_apply_approved_create_dailyplan_proposal_requires_approved_status(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.context_dailyplan,
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
                                        "food_id": self.chicken.id,
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
            "proposal_is_not_applicable",
        ):
            apply_approved_create_dailyplan_proposal(
                user=self.user,
                proposal=proposal,
            )

        self.assertEqual(DailyPlan.objects.count(), 2)
        self.assertEqual(Meal.objects.count(), 0)

    def test_apply_approved_create_dailyplan_proposal_rejects_meal_payload(self):
        proposal = NutritionProposal.objects.create(
            dailyplan=self.context_dailyplan,
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
                            "food_id": self.chicken.id,
                            "quantity": 200,
                        },
                    ],
                },
            },
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_apply_intent_must_be_create_dailyplan",
        ):
            apply_approved_create_dailyplan_proposal(
                user=self.user,
                proposal=proposal,
            )

        self.assertEqual(DailyPlan.objects.count(), 2)
        self.assertEqual(Meal.objects.count(), 0)

    def test_apply_approved_create_dailyplan_proposal_blocks_double_application(self):
        proposal = self._create_approved_create_dailyplan_proposal()

        apply_approved_create_dailyplan_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()

        with self.assertRaisesMessage(
            ValueError,
            "proposal_is_not_applicable",
        ):
            apply_approved_create_dailyplan_proposal(
                user=self.user,
                proposal=proposal,
            )

        self.assertEqual(DailyPlan.objects.count(), 3)

    def test_apply_approved_create_dailyplan_proposal_creates_audit_event(self):
        proposal = self._create_approved_create_dailyplan_proposal()

        result = apply_approved_create_dailyplan_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()

        audit_event = proposal.audit_events.get(
            action="applied",
        )

        self.assertEqual(audit_event.actor, self.user)
        self.assertEqual(audit_event.status_before, NutritionProposal.STATUS_APPROVED)
        self.assertEqual(audit_event.status_after, NutritionProposal.STATUS_APPLIED)
        self.assertEqual(audit_event.message, "Create dailyplan proposal applied.")
        self.assertEqual(audit_event.metadata["intent"], "create_dailyplan")
        self.assertEqual(audit_event.metadata["dailyplan_id"], result.dailyplan.id)
        self.assertEqual(audit_event.metadata["dailyplan_name"], "Día entrenamiento IA")
        self.assertEqual(audit_event.metadata["source"], DailyPlan.SOURCE_AI)
        self.assertEqual(len(audit_event.metadata["meals"]), 2)

    def test_apply_approved_create_dailyplan_proposal_populates_nutrition_totals(self):
        proposal = self._create_approved_create_dailyplan_proposal()

        result = apply_approved_create_dailyplan_proposal(
            user=self.user,
            proposal=proposal,
        )

        dailyplan = result.dailyplan
        dailyplan.refresh_from_db()

        self.assertAlmostEqual(dailyplan.protein, 66.35)
        self.assertAlmostEqual(dailyplan.carbs, 62.5)
        self.assertAlmostEqual(dailyplan.fat, 7.95)
        self.assertAlmostEqual(dailyplan.total_kcal, 586.95)