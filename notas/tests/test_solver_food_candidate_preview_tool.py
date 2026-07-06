from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.ai_tools.read_tools import preview_nutrition_solver_candidates_tool
from notas.domain.models import Food


class SolverFoodCandidatePreviewToolTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="felipe")

    def test_preview_tool_returns_solver_candidates_without_catalog_payloads(self):
        food = Food.objects.create(
            name="Pechuga de pollo",
            protein=31,
            carbs=0,
            fat=3,
            is_global=True,
            is_active=True,
            visibility=Food.VISIBILITY_CORE,
            solver_enabled=True,
            is_verified=True,
            data_quality_score=90,
            catalog_food_id=999,
            catalog_snapshot_payload={"provider": "external"},
        )
        Food.objects.create(
            name="Oculto",
            protein=10,
            carbs=10,
            fat=10,
            is_global=True,
            is_active=True,
            visibility=Food.VISIBILITY_HIDDEN,
            solver_enabled=True,
        )

        result = preview_nutrition_solver_candidates_tool(
            self.user,
            search="pollo",
            limit=10,
            include_extended=True,
        )

        self.assertTrue(result.ok)
        preview = result.data["solver_candidate_preview"]
        self.assertEqual(preview["count"], 1)
        candidate = preview["candidates"][0]
        self.assertEqual(candidate["food_id"], food.id)
        self.assertEqual(candidate["name"], "Pechuga de pollo")
        self.assertEqual(candidate["role"], "protein")
        self.assertNotIn("catalog_food_id", candidate)
        self.assertNotIn("catalog_snapshot_payload", candidate)

        boundary = result.data["source_boundary"]
        self.assertEqual(boundary["source"], "notas.Food")
        self.assertEqual(boundary["candidate_contract"], "nutrition_solver.domain.models.SolverFood")
        self.assertFalse(boundary["catalog_fields_exposed"])
        self.assertFalse(boundary["external_payloads_exposed"])
        self.assertFalse(boundary["writes_allowed"])

    def test_preview_tool_respects_core_only_filter(self):
        Food.objects.create(
            name="Arroz extendido",
            protein=2.7,
            carbs=28,
            fat=1,
            is_global=True,
            is_active=True,
            visibility=Food.VISIBILITY_EXTENDED,
            solver_enabled=True,
        )
        Food.objects.create(
            name="Papa core",
            protein=2,
            carbs=20,
            fat=0.1,
            is_global=True,
            is_active=True,
            visibility=Food.VISIBILITY_CORE,
            solver_enabled=True,
        )

        result = preview_nutrition_solver_candidates_tool(
            self.user,
            limit=10,
            include_extended=False,
        )

        self.assertTrue(result.ok)
        names = [candidate["name"] for candidate in result.data["solver_candidate_preview"]["candidates"]]
        self.assertEqual(names, ["Papa core"])
