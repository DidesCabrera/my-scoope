from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.ai_intake.dailyplan_generator import (
    DAILYPLAN_GENERATOR_VERSION,
    build_dailyplan_payload_from_brief,
    build_dailyplan_target_plan,
)
from notas.application.ai_intake.nutrition_brief import NutritionBrief
from notas.application.queries.proposal_simulation_queries import simulate_proposal_payload
from notas.domain.models import Food


class DailyPlanGeneratorNutritionEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="felipe")
        self._food("Pechuga de pollo", protein=31, carbs=0, fat=3.6, group="proteins", default=160, minimum=90, maximum=260)
        self._food("Arroz cocido", protein=2.7, carbs=28, fat=0.3, group="cereals", default=160, minimum=45, maximum=240)
        self._food("Palta", protein=2, carbs=8.5, fat=14.7, group="fats", default=30, minimum=5, maximum=70)
        self._food("Tomate", protein=0.9, carbs=3.9, fat=0.2, group="vegetables", default=100, minimum=50, maximum=180)
        self._food("Yogur griego", protein=10, carbs=4, fat=2, group="dairy", default=170, minimum=90, maximum=220)
        self._food("Avena", protein=13, carbs=68, fat=7, group="cereals", default=60, minimum=25, maximum=120)

    def _food(self, name, *, protein, carbs, fat, group, default, minimum, maximum):
        return Food.objects.create(
            name=name,
            protein=protein,
            carbs=carbs,
            fat=fat,
            created_by=None,
            is_global=True,
            is_active=True,
            is_verified=True,
            food_group=group,
            default_portion_g=default,
            min_portion_g=minimum,
            max_portion_g=maximum,
            portion_step_g=5,
            data_quality_score=90,
        )

    def test_generator_uses_nutrition_engine_solver_version(self):
        self.assertEqual(DAILYPLAN_GENERATOR_VERSION, "nutrition_engine_v6_strict_validator")

    def test_payload_uses_solver_portions_and_validates_against_targets(self):
        brief = NutritionBrief(
            raw_prompt="quiero bajar grasa con 4 comidas",
            goal="fat_loss",
            meals_per_day=4,
            weight_kg=82,
            height_cm=178,
            age_years=36,
            sex="male",
            activity_level="moderate",
            style_preferences=["simple"],
        )
        target_plan = build_dailyplan_target_plan(user=self.user, brief=brief)
        payload = build_dailyplan_payload_from_brief(
            user=self.user,
            brief=brief,
            target_plan=target_plan,
        )
        simulation = simulate_proposal_payload(user=self.user, payload=payload).as_dict()
        kpis = simulation["dailyplan"]["kpis"]

        self.assertEqual(payload["intent"], "create_dailyplan")
        self.assertEqual(len(payload["dailyplan"]["meals"]), 4)
        self.assertLess(abs(kpis["total_kcal"] - target_plan.total_kcal) / target_plan.total_kcal, 0.20)
        self.assertLess(abs(kpis["protein"] - target_plan.protein) / target_plan.protein, 0.25)

    def test_payload_respects_excluded_foods_before_solver(self):
        brief = NutritionBrief(
            raw_prompt="quiero bajar grasa sin arroz",
            goal="fat_loss",
            meals_per_day=3,
            weight_kg=78,
            height_cm=176,
            age_years=35,
            sex="male",
            activity_level="light",
            excluded_foods=["arroz"],
            style_preferences=["simple"],
        )
        payload = build_dailyplan_payload_from_brief(user=self.user, brief=brief)
        used_food_ids = [
            item["food_id"]
            for meal in payload["dailyplan"]["meals"]
            for item in meal["meal"]["foods"]
        ]
        rice_id = Food.objects.get(name="Arroz cocido").id

        self.assertNotIn(rice_id, used_food_ids)
