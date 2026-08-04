from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.queries.solver_food_candidates import (
    build_solver_food_candidate,
    list_solver_food_candidates,
)
from notas.domain.models import Food
from nutrition_solver.domain.models import PortionBounds, SolverFood


class SolverFoodCandidatesQueryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="felipe")
        self.other_user = User.objects.create_user(username="other")

    def test_lists_only_solver_ready_operational_foods_readable_by_user(self):
        chicken = self._food(
            "Pechuga de pollo",
            protein=31,
            carbs=0,
            fat=3,
            is_global=True,
            visibility=Food.VISIBILITY_CORE,
            solver_enabled=True,
            is_verified=True,
            data_quality_score=95,
            min_portion_g=90,
            max_portion_g=260,
            portion_step_g=10,
            catalog_food_id=123,
            catalog_snapshot_payload={"external": "payload"},
        )
        self._food(
            "Oculto solver",
            protein=10,
            carbs=10,
            fat=10,
            is_global=True,
            visibility=Food.VISIBILITY_HIDDEN,
            solver_enabled=True,
        )
        self._food(
            "No habilitado",
            protein=10,
            carbs=10,
            fat=10,
            is_global=True,
            visibility=Food.VISIBILITY_CORE,
            solver_enabled=False,
        )
        self._food(
            "Privado de otro usuario",
            protein=10,
            carbs=10,
            fat=10,
            created_by=self.other_user,
            visibility=Food.VISIBILITY_CORE,
            solver_enabled=True,
        )

        result = list_solver_food_candidates(self.user)

        self.assertEqual(result.count, 1)
        candidate = result.candidates[0]
        self.assertIsInstance(candidate, SolverFood)
        self.assertEqual(candidate.food_id, chicken.id)
        self.assertEqual(candidate.role, "protein")
        self.assertEqual(candidate.bounds, PortionBounds(90, 260, 10).normalized())

        payload = result.as_dict()
        self.assertEqual(payload["candidates"][0]["food_id"], chicken.id)
        self.assertNotIn("catalog_food_id", payload["candidates"][0])
        self.assertNotIn("catalog_snapshot_payload", payload["candidates"][0])

    def test_search_and_include_extended_filter_are_applied(self):
        self._food(
            "Arroz integral",
            protein=2.7,
            carbs=28,
            fat=1,
            is_global=True,
            visibility=Food.VISIBILITY_EXTENDED,
            solver_enabled=True,
            canonical_name="arroz integral cocido",
        )
        self._food(
            "Papa cocida",
            protein=2,
            carbs=20,
            fat=0.1,
            is_global=True,
            visibility=Food.VISIBILITY_CORE,
            solver_enabled=True,
        )

        extended = list_solver_food_candidates(self.user, search="arroz")
        core_only = list_solver_food_candidates(self.user, search="arroz", include_extended=False)

        self.assertEqual([candidate.name for candidate in extended.candidates], ["Arroz integral"])
        self.assertEqual(core_only.candidates, ())

    def test_build_candidate_uses_safe_defaults_and_clamps_invalid_bounds(self):
        food = self._food(
            "Aceite de oliva",
            protein=0,
            carbs=0,
            fat=100,
            is_global=True,
            visibility=Food.VISIBILITY_CORE,
            solver_enabled=True,
            min_portion_g=50,
            max_portion_g=10,
            portion_step_g=0,
        )

        candidate = build_solver_food_candidate(food)

        self.assertEqual(candidate.role, "fat")
        self.assertEqual(candidate.bounds.minimum_g, 50)
        self.assertEqual(candidate.bounds.maximum_g, 50)
        self.assertEqual(candidate.bounds.step_g, 5)
        self.assertEqual(candidate.macros_for_quantity(10).fat, 10)

    def _food(self, name, *, protein, carbs, fat, **kwargs):
        defaults = {
            "name": name,
            "protein": protein,
            "carbs": carbs,
            "fat": fat,
            "created_by": None,
            "is_global": False,
            "is_active": True,
            "visibility": Food.VISIBILITY_EXTENDED,
            "solver_enabled": False,
        }
        defaults.update(kwargs)
        return Food.objects.create(**defaults)
