from __future__ import annotations

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.ai_intake.dailyplan_generator import (
    DAILYPLAN_GENERATOR_VERSION,
    build_dailyplan_payload_from_brief,
    build_dailyplan_target_plan,
    generate_dailyplan_proposal_from_brief_proposal,
)
from notas.application.ai_intake.nutrition_brief import NutritionBrief
from notas.application.ai_intake.proposal_from_brief import create_nutrition_brief_proposal
from notas.application.dto.proposal_payloads import CREATE_DAILYPLAN_INTENT
from notas.application.queries.proposal_simulation_queries import simulate_proposal_payload
from notas.domain.models import Food, NutritionProposal, WeightLog


class AiIntakeDailyPlanGeneratorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="felipe", password="test")
        self.foods = self._create_food_catalog()

    def _create_food_catalog(self):
        return {
            "fish": Food.objects.create(
                name="Pescado blanco",
                protein=22,
                carbs=0,
                fat=2,
                created_by=None,
                is_global=True,
                is_verified=True,
                food_group="pescados",
                data_quality_score=90,
                default_portion_g=180,
                min_portion_g=90,
                max_portion_g=260,
                portion_step_g=5,
            ),
            "chicken": Food.objects.create(
                name="Pechuga de pollo",
                protein=31,
                carbs=0,
                fat=3,
                created_by=None,
                is_global=True,
                is_verified=True,
                food_group="carnes",
                data_quality_score=95,
                default_portion_g=170,
                min_portion_g=90,
                max_portion_g=260,
                portion_step_g=5,
            ),
            "yogurt": Food.objects.create(
                name="Yogur griego natural",
                protein=10,
                carbs=4,
                fat=0.4,
                created_by=None,
                is_global=True,
                is_verified=True,
                food_group="lácteos",
                data_quality_score=85,
                default_portion_g=170,
                min_portion_g=100,
                max_portion_g=250,
                portion_step_g=5,
            ),
            "rice": Food.objects.create(
                name="Arroz cocido",
                protein=2.7,
                carbs=28,
                fat=0.3,
                created_by=None,
                is_global=True,
                is_verified=True,
                food_group="cereales",
                data_quality_score=90,
                default_portion_g=150,
                min_portion_g=45,
                max_portion_g=240,
                portion_step_g=5,
            ),
            "oats": Food.objects.create(
                name="Avena",
                protein=13,
                carbs=60,
                fat=7,
                created_by=None,
                is_global=True,
                is_verified=True,
                food_group="cereales",
                data_quality_score=88,
                default_portion_g=60,
                min_portion_g=25,
                max_portion_g=120,
                portion_step_g=5,
            ),
            "avocado": Food.objects.create(
                name="Palta",
                protein=2,
                carbs=9,
                fat=15,
                created_by=None,
                is_global=True,
                is_verified=True,
                food_group="grasas",
                data_quality_score=80,
                default_portion_g=30,
                min_portion_g=10,
                max_portion_g=40,
                portion_step_g=5,
            ),
            "tomato": Food.objects.create(
                name="Tomate",
                protein=1,
                carbs=4,
                fat=0.2,
                created_by=None,
                is_global=True,
                is_verified=True,
                food_group="verduras",
                data_quality_score=80,
                default_portion_g=100,
                min_portion_g=50,
                max_portion_g=180,
                portion_step_g=5,
            ),
        }

    def test_infers_fat_loss_targets_from_current_weight_when_brief_has_no_targets(self):
        WeightLog.objects.create(user=self.user, date=date(2026, 6, 28), weight_kg=80)
        brief = NutritionBrief(
            raw_prompt="quiero bajar grasa, 4 comidas, simple",
            goal="fat_loss",
            meals_per_day=4,
            weight_kg=80,
            height_cm=175,
            age_years=30,
            sex="male",
            activity_level="moderate",
            style_preferences=["simple"],
        )

        target_plan = build_dailyplan_target_plan(user=self.user, brief=brief)

        self.assertLess(target_plan.total_kcal, target_plan.estimated_tdee)
        self.assertGreater(target_plan.estimated_tdee, 2500)
        self.assertEqual(target_plan.energy_adjustment, "deficit_moderate")
        self.assertGreaterEqual(target_plan.protein, 140)
        self.assertTrue(target_plan.estimated_targets["total_kcal"])
        self.assertTrue(target_plan.estimated_targets["protein"])
        self.assertFalse(target_plan.explicit_targets["total_kcal"])

    def test_builds_valid_payload_with_meal_targets_and_respects_excluded_foods(self):
        brief = NutritionBrief(
            raw_prompt="quiero bajar grasa, 4 comidas, simple, sin pescado",
            goal="fat_loss",
            meals_per_day=4,
            weight_kg=80,
            height_cm=175,
            age_years=30,
            sex="male",
            activity_level="moderate",
            style_preferences=["simple"],
            excluded_foods=["pescado"],
        )

        payload = build_dailyplan_payload_from_brief(user=self.user, brief=brief)
        dailyplan = payload["dailyplan"]

        self.assertEqual(payload["intent"], CREATE_DAILYPLAN_INTENT)
        self.assertEqual(len(dailyplan["meals"]), 4)

        used_food_ids = {
            food["food_id"]
            for dailyplan_meal in dailyplan["meals"]
            for food in dailyplan_meal["meal"]["foods"]
        }
        self.assertNotIn(self.foods["fish"].id, used_food_ids)
        self.assertIn(self.foods["chicken"].id, used_food_ids)

        simulation = simulate_proposal_payload(user=self.user, payload=payload).as_dict()
        kpis = simulation["dailyplan"]["kpis"]
        self.assertGreater(kpis["total_kcal"], 1200)
        self.assertGreater(kpis["protein"], 80)

    def test_uses_explicit_targets_when_the_brief_provides_them(self):
        brief = NutritionBrief(
            raw_prompt="quiero bajar grasa, 4 comidas, simple, 1900 kcal, 150 proteina",
            goal="fat_loss",
            meals_per_day=4,
            calorie_target=1900,
            protein_target=150,
            style_preferences=["simple"],
        )

        target_plan = build_dailyplan_target_plan(user=self.user, brief=brief)

        self.assertEqual(target_plan.total_kcal, 1900)
        self.assertEqual(target_plan.protein, 150)
        self.assertTrue(target_plan.explicit_targets["total_kcal"])
        self.assertTrue(target_plan.explicit_targets["protein"])
        self.assertFalse(target_plan.estimated_targets["total_kcal"])

    def test_generated_proposal_stores_targets_generator_metadata_and_target_comparison(self):
        brief = NutritionBrief(
            raw_prompt="quiero bajar grasa, 4 comidas, simple, sin pescado",
            goal="fat_loss",
            meals_per_day=4,
            weight_kg=80,
            height_cm=175,
            age_years=30,
            sex="male",
            activity_level="moderate",
            style_preferences=["simple"],
            excluded_foods=["pescado"],
        )
        source_proposal = create_nutrition_brief_proposal(user=self.user, brief=brief).proposal

        result = generate_dailyplan_proposal_from_brief_proposal(
            user=self.user,
            source_proposal=source_proposal,
        )

        proposal = result.proposal
        self.assertEqual(proposal.proposed_payload["intent"], CREATE_DAILYPLAN_INTENT)
        self.assertEqual(proposal.current_snapshot["generator_version"], DAILYPLAN_GENERATOR_VERSION)
        self.assertEqual(proposal.validation_summary["generator"]["version"], DAILYPLAN_GENERATOR_VERSION)
        self.assertEqual(proposal.validation_summary["generator"]["meal_templates"][0]["kind"], "breakfast")
        self.assertTrue(proposal.targets["estimated_targets"]["total_kcal"])
        self.assertIn("estimated_tdee", proposal.targets)
        self.assertGreater(proposal.targets["estimated_tdee"], proposal.targets["total_kcal"])
        self.assertIn("total_kcal", proposal.validation_summary["target_comparison"])
        self.assertEqual(
            proposal.validation_summary["target_comparison"]["total_kcal"]["is_estimated_target"],
            True,
        )
        self.assertEqual(
            proposal.validation_summary["engine_validation"]["kind"],
            "strict_dailyplan_nutrition_validation",
        )
        self.assertIn(
            proposal.validation_summary["engine_validation"]["status"],
            {"ok", "warning", "error"},
        )
        self.assertIn(
            "strict",
            proposal.validation_summary["engine_validation"],
        )
        self.assertEqual(NutritionProposal.objects.filter(created_by=self.user).count(), 2)
