from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.services.commands.proposal_commands import (
    apply_approved_create_meal_proposal,
)
from notas.domain.models import (
    DailyPlan,
    Food,
    Meal,
    MealFood,
    NutritionProposal,
)


class ApplyCreateMealProposalCommandTests(TestCase):
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

    def _create_approved_create_meal_proposal(self, foods=None):
        return NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": foods or [
                        {
                            "food_id": self.chicken.id,
                            "quantity": 200,
                            "unit": "g",
                        },
                        {
                            "food_id": self.rice.id,
                            "quantity": 100,
                            "unit": "g",
                        },
                    ],
                },
            },
        )

    def test_apply_approved_create_meal_proposal_creates_real_meal(self):
        proposal = self._create_approved_create_meal_proposal()

        before_meal_count = Meal.objects.count()
        before_mealfood_count = MealFood.objects.count()
        before_dailyplan_count = DailyPlan.objects.count()

        result = apply_approved_create_meal_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()

        self.assertEqual(Meal.objects.count(), before_meal_count + 1)
        self.assertEqual(MealFood.objects.count(), before_mealfood_count + 2)
        self.assertEqual(DailyPlan.objects.count(), before_dailyplan_count)

        meal = result.meal

        self.assertEqual(meal.name, "Almuerzo IA")
        self.assertEqual(meal.created_by, self.user)
        self.assertFalse(meal.is_public)
        self.assertTrue(meal.is_forkable)
        self.assertFalse(meal.is_copiable)
        self.assertFalse(meal.is_draft)
        self.assertIsNone(meal.pending_dailyplan)
        self.assertIsNone(meal.forked_from)
        self.assertIsNone(meal.original_author)

        meal_foods = list(
            meal.meal_food_set
            .select_related("food")
            .order_by("order", "id")
        )

        self.assertEqual(len(meal_foods), 2)
        self.assertEqual(meal_foods[0].food, self.chicken)
        self.assertEqual(meal_foods[0].quantity, 200.0)
        self.assertEqual(meal_foods[0].order, 1)
        self.assertEqual(meal_foods[1].food, self.rice)
        self.assertEqual(meal_foods[1].quantity, 100.0)
        self.assertEqual(meal_foods[1].order, 2)

        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPLIED)
        self.assertEqual(proposal.applied_by, self.user)
        self.assertIsNotNone(proposal.applied_at)

    def test_apply_approved_create_meal_proposal_allows_system_food(self):
        proposal = self._create_approved_create_meal_proposal(
            foods=[
                {
                    "food_id": self.system_banana.id,
                    "quantity": 150,
                    "unit": "g",
                },
            ],
        )

        result = apply_approved_create_meal_proposal(
            user=self.user,
            proposal=proposal,
        )

        meal_food = result.meal.meal_food_set.select_related("food").get()

        self.assertEqual(meal_food.food, self.system_banana)
        self.assertEqual(meal_food.quantity, 150.0)

    def test_apply_approved_create_meal_proposal_rejects_private_other_food(self):
        proposal = self._create_approved_create_meal_proposal(
            foods=[
                {
                    "food_id": self.private_other_food.id,
                    "quantity": 100,
                    "unit": "g",
                },
            ],
        )

        before_meal_count = Meal.objects.count()
        before_mealfood_count = MealFood.objects.count()

        with self.assertRaisesMessage(
            ValueError,
            "proposal_apply_food_not_available",
        ):
            apply_approved_create_meal_proposal(
                user=self.user,
                proposal=proposal,
            )

        proposal.refresh_from_db()

        self.assertEqual(Meal.objects.count(), before_meal_count)
        self.assertEqual(MealFood.objects.count(), before_mealfood_count)
        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPROVED)
        self.assertIsNone(proposal.applied_by)
        self.assertIsNone(proposal.applied_at)

    def test_apply_approved_create_meal_proposal_requires_owner(self):
        proposal = self._create_approved_create_meal_proposal()

        with self.assertRaisesMessage(
            ValueError,
            "proposal_review_not_allowed",
        ):
            apply_approved_create_meal_proposal(
                user=self.other_user,
                proposal=proposal,
            )

        proposal.refresh_from_db()

        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPROVED)
        self.assertEqual(Meal.objects.count(), 0)

    def test_apply_approved_create_meal_proposal_requires_approved_status(self):
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
                            "food_id": self.chicken.id,
                            "quantity": 200,
                        },
                    ],
                },
            },
        )

        with self.assertRaisesMessage(
            ValueError,
            "proposal_is_not_applicable",
        ):
            apply_approved_create_meal_proposal(
                user=self.user,
                proposal=proposal,
            )

        self.assertEqual(Meal.objects.count(), 0)

    def test_apply_approved_create_meal_proposal_rejects_dailyplan_payload(self):
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
                                "name": "Desayuno IA",
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
            "proposal_apply_intent_must_be_create_meal",
        ):
            apply_approved_create_meal_proposal(
                user=self.user,
                proposal=proposal,
            )

        self.assertEqual(Meal.objects.count(), 0)

    def test_apply_approved_create_meal_proposal_blocks_double_application(self):
        proposal = self._create_approved_create_meal_proposal()

        apply_approved_create_meal_proposal(
            user=self.user,
            proposal=proposal,
        )

        proposal.refresh_from_db()

        with self.assertRaisesMessage(
            ValueError,
            "proposal_is_not_applicable",
        ):
            apply_approved_create_meal_proposal(
                user=self.user,
                proposal=proposal,
            )

        self.assertEqual(Meal.objects.count(), 1)

    def test_apply_approved_create_meal_proposal_creates_audit_event(self):
        proposal = self._create_approved_create_meal_proposal()

        result = apply_approved_create_meal_proposal(
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
        self.assertEqual(audit_event.message, "Create meal proposal applied.")
        self.assertEqual(audit_event.metadata["intent"], "create_meal")
        self.assertEqual(audit_event.metadata["meal_id"], result.meal.id)
        self.assertEqual(audit_event.metadata["meal_name"], "Almuerzo IA")
        self.assertEqual(len(audit_event.metadata["foods"]), 2)

    def test_apply_approved_create_meal_proposal_populates_nutrition_cache(self):
        proposal = self._create_approved_create_meal_proposal()

        result = apply_approved_create_meal_proposal(
            user=self.user,
            proposal=proposal,
        )

        meal = result.meal
        meal.refresh_from_db()

        self.assertAlmostEqual(meal.protein, 64.7)
        self.assertAlmostEqual(meal.carbs, 28.0)
        self.assertAlmostEqual(meal.fat, 7.5)
        self.assertAlmostEqual(meal.total_kcal, 438.3)