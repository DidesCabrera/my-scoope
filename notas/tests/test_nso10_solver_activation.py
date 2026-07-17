from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from notas.application.ai_intake.dailyplan_generator import (
    _build_dailyplan_payload_with_solver_summary,
    build_dailyplan_payload_from_brief,
    build_dailyplan_target_plan,
)
from notas.application.ai_intake.nutrition_brief import NutritionBrief
from notas.domain.models import Food


class NutritionSolverNSO10ActivationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="nso10")
        self.protein_1 = self._food(1, "Protein one", ("primary_protein",), 30, 0, 5)
        self.protein_2 = self._food(2, "Protein two", ("primary_protein",), 22, 3, 10)
        self.carb_1 = self._food(3, "Rice option", ("starch_or_carbohydrate",), 5, 70, 6)
        self.carb_2 = self._food(4, "Oat option", ("starch_or_carbohydrate",), 8, 55, 4)
        self.brief = NutritionBrief(
            raw_prompt="plan de dos comidas",
            goal="maintenance",
            meals_per_day=2,
            calorie_target=1600,
            protein_target=120,
            carb_target=180,
            fat_target=45,
            excluded_foods=("rice",),
        )

    def _food(self, position, name, roles, protein, carbs, fat):
        return Food.objects.create(
            name=name,
            canonical_name=f"solver food {position}",
            protein=protein,
            carbs=carbs,
            fat=fat,
            created_by=None,
            is_global=True,
            is_active=True,
            is_verified=True,
            solver_enabled=True,
            visibility=Food.VISIBILITY_CORE,
            min_portion_g=20,
            max_portion_g=300,
            portion_step_g=10,
            data_quality_score=95,
            solver_capabilities={
                "schema_version": "solver_food_capabilities.v1",
                "source": "test",
                "values": {"functional_roles": list(roles)},
                "confidence": {"functional_roles": 95},
            },
        )

    @override_settings(NUTRITION_SOLVER_BACKEND="cp_sat_v1", NUTRITION_SOLVER_SHADOW_ENABLED=False)
    def test_cp_sat_can_be_activated_for_dailyplan_generation(self):
        payload = build_dailyplan_payload_from_brief(user=self.user, brief=self.brief)

        self.assertEqual(len(payload["dailyplan"]["meals"]), 2)
        self.assertTrue(all("NSO" in item["meal"]["name"] for item in payload["dailyplan"]["meals"]))
        selected_ids = {
            food["food_id"]
            for item in payload["dailyplan"]["meals"]
            for food in item["meal"]["foods"]
        }
        self.assertNotIn(self.carb_1.id, selected_ids)

    @override_settings(
        NUTRITION_SOLVER_BACKEND="heuristic_v2",
        NUTRITION_SOLVER_SHADOW_ENABLED=True,
        NUTRITION_SOLVER_SHADOW_BACKEND="cp_sat_v1",
    )
    def test_shadow_mode_preserves_legacy_visible_payload(self):
        target_plan = build_dailyplan_target_plan(user=self.user, brief=self.brief)
        payload, summary = _build_dailyplan_payload_with_solver_summary(
            user=self.user,
            brief=self.brief,
            target_plan=target_plan,
        )

        self.assertTrue(all(" IA " in item["meal"]["name"] for item in payload["dailyplan"]["meals"]))
        self.assertEqual(summary["active_backend"], "legacy_generator_v6")
        self.assertEqual(summary["shadow_backend"], "cp_sat_v1")
        self.assertEqual(summary["visible_payload_source"], "legacy_generator_v6")
