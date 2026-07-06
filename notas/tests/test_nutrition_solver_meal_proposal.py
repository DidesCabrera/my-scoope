from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.ai_tools.proposal_tools import (
    create_nutrition_solver_meal_proposal_tool,
)
from notas.application.proposals.solver_meal_proposals import (
    create_solver_generated_meal_proposal,
)
from notas.domain.models import DailyPlan, Food, NutritionProposal


class NutritionSolverMealProposalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="felipe")
        self.dailyplan = DailyPlan.objects.create(
            name="Training Day",
            created_by=self.user,
            is_public=False,
            is_draft=False,
        )
        self.chicken = self._food(
            "Pechuga de pollo",
            protein=31,
            carbs=0,
            fat=3,
            food_group="carnes",
            visibility=Food.VISIBILITY_CORE,
            solver_enabled=True,
            min_portion_g=80,
            max_portion_g=260,
            catalog_food_id=999,
            catalog_snapshot_payload={"provider": "external"},
        )
        self.rice = self._food(
            "Arroz cocido",
            protein=2.7,
            carbs=28,
            fat=0.3,
            food_group="cereales",
            visibility=Food.VISIBILITY_CORE,
            solver_enabled=True,
            min_portion_g=60,
            max_portion_g=320,
        )
        self.oil = self._food(
            "Aceite de oliva",
            protein=0,
            carbs=0,
            fat=100,
            food_group="aceites",
            visibility=Food.VISIBILITY_CORE,
            solver_enabled=True,
            min_portion_g=5,
            max_portion_g=35,
        )
        self._food(
            "Oculto catalogado",
            protein=10,
            carbs=10,
            fat=10,
            visibility=Food.VISIBILITY_HIDDEN,
            solver_enabled=True,
            catalog_food_id=123,
        )

    def test_creates_reviewable_meal_proposal_from_solver_result(self):
        result = create_solver_generated_meal_proposal(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            title="Almuerzo solver",
            target={"kcal": 520, "protein": 45, "carbs": 65, "fat": 12},
            limit=10,
            meal_slot="Almuerzo",
        )

        proposal = result.proposal
        proposal.refresh_from_db()

        self.assertEqual(proposal.status, NutritionProposal.STATUS_PENDING_REVIEW)
        self.assertEqual(proposal.dailyplan, self.dailyplan)
        self.assertEqual(proposal.proposed_payload["intent"], "create_meal")
        self.assertEqual(proposal.proposed_payload["meal"]["name"], "Almuerzo solver")
        self.assertGreaterEqual(len(proposal.proposed_payload["meal"]["foods"]), 1)
        self.assertEqual(proposal.targets["kcal"], 520.0)

        solver_summary = proposal.validation_summary["nutrition_solver"]
        self.assertIn(solver_summary["status"], {"optimal", "acceptable", "partial"})
        self.assertEqual(solver_summary["version"], "nutrition_solver_meal_proposal_v1")
        self.assertEqual(solver_summary["source_boundary"]["candidate_source"], "notas.Food")
        self.assertFalse(solver_summary["source_boundary"]["catalog_fields_exposed"])
        self.assertFalse(solver_summary["source_boundary"]["external_payloads_exposed"])
        self.assertFalse(solver_summary["source_boundary"]["applies_changes"])
        self.assertTrue(solver_summary["source_boundary"]["requires_human_review"])

        payload_text = str(proposal.validation_summary) + str(proposal.proposed_payload)
        self.assertNotIn("catalog_food_id", payload_text)
        self.assertNotIn("catalog_snapshot_payload", payload_text)
        self.assertNotIn("provider", payload_text)

    def test_tool_creates_reviewable_proposal_without_applying_changes(self):
        result = create_nutrition_solver_meal_proposal_tool(
            self.user,
            dailyplan_id=self.dailyplan.id,
            title="Cena solver",
            target={"total_kcal": 480, "protein": 40, "carbs": 55, "fat": 10},
            meal_slot="Cena",
        )

        self.assertTrue(result.ok)
        proposal = result.data["proposal"]
        self.assertEqual(proposal["status"], NutritionProposal.STATUS_PENDING_REVIEW)
        self.assertEqual(proposal["proposed_payload"]["intent"], "create_meal")
        self.assertFalse(result.data["nutrition_solver"]["applies_changes"])
        self.assertTrue(result.data["nutrition_solver"]["requires_human_review"])
        self.assertIn(
            result.data["nutrition_solver"]["optimization_result"]["status"],
            {"optimal", "acceptable", "partial"},
        )

    def test_impossible_solver_result_is_tool_error_not_proposal(self):
        result = create_nutrition_solver_meal_proposal_tool(
            self.user,
            dailyplan_id=self.dailyplan.id,
            title="Sin candidatos",
            target={"kcal": 480, "protein": 40, "carbs": 55, "fat": 10},
            search="no existe",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "nutrition_solver_meal_proposal_impossible")
        self.assertEqual(NutritionProposal.objects.filter(title="Sin candidatos").count(), 0)

    def _food(self, name, *, protein, carbs, fat, **kwargs):
        defaults = {
            "name": name,
            "protein": protein,
            "carbs": carbs,
            "fat": fat,
            "created_by": None,
            "is_global": True,
            "is_active": True,
            "visibility": Food.VISIBILITY_CORE,
            "solver_enabled": True,
        }
        defaults.update(kwargs)
        return Food.objects.create(**defaults)
