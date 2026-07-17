from django.test import SimpleTestCase

from notas.application.ai_intake.dailyplan_generator import (
    DAILYPLAN_GENERATOR_VERSION,
    DailyPlanGeneratorFood,
    _select_foods_for_meal,
)
from notas.application.nutrition_engine.meal_templates import build_dailyplan_meal_templates
from notas.application.nutrition_engine.candidate_selector import (
    CandidateSelectionError,
    NutritionFoodCandidate,
    classify_food_for_role,
    select_meal_food_candidates,
)


class NutritionEngineCandidateSelectorTests(SimpleTestCase):
    def test_selects_distinct_roles_and_respects_hard_exclusions(self):
        foods = [
            NutritionFoodCandidate(
                food_id=1,
                name="Pechuga de pollo",
                protein=31,
                carbs=0,
                fat=3,
                kcal_per_100g=151,
                food_group="carnes",
                is_verified=True,
                data_quality_score=90,
            ),
            NutritionFoodCandidate(
                food_id=2,
                name="Arroz cocido",
                protein=2.5,
                carbs=28,
                fat=0.3,
                kcal_per_100g=125,
                food_group="cereales",
                is_verified=True,
                data_quality_score=90,
            ),
            NutritionFoodCandidate(
                food_id=3,
                name="Quinoa cocida",
                protein=4.4,
                carbs=21,
                fat=1.9,
                kcal_per_100g=120,
                food_group="cereales",
                is_verified=True,
                data_quality_score=70,
            ),
            NutritionFoodCandidate(
                food_id=4,
                name="Palta",
                protein=2,
                carbs=8,
                fat=15,
                kcal_per_100g=175,
                food_group="grasas",
                is_verified=True,
                data_quality_score=85,
            ),
            NutritionFoodCandidate(
                food_id=5,
                name="Tomate",
                protein=1,
                carbs=4,
                fat=0.2,
                kcal_per_100g=22,
                food_group="verduras",
                is_verified=True,
                data_quality_score=85,
            ),
        ]

        selection = select_meal_food_candidates(
            foods=foods,
            excluded_terms=["arroz"],
        )

        self.assertEqual(selection.protein_id, 1)
        self.assertEqual(selection.carb_id, 3)
        self.assertEqual(selection.fat_id, 4)
        self.assertEqual(selection.vegetable_id, 5)
        self.assertNotEqual(selection.protein_id, selection.carb_id)
        self.assertNotIn(2, selection.selected_roles.values())

    def test_preferences_can_prioritize_a_valid_role_candidate(self):
        foods = [
            NutritionFoodCandidate(
                food_id=1,
                name="Pechuga de pollo",
                protein=31,
                carbs=0,
                fat=3,
                kcal_per_100g=151,
                food_group="carnes",
                is_verified=True,
                data_quality_score=90,
            ),
            NutritionFoodCandidate(
                food_id=2,
                name="Pavo cocido",
                protein=29,
                carbs=0,
                fat=2,
                kcal_per_100g=134,
                food_group="carnes",
                is_verified=True,
                data_quality_score=70,
            ),
            NutritionFoodCandidate(
                food_id=3,
                name="Papa cocida",
                protein=2,
                carbs=20,
                fat=0.1,
                kcal_per_100g=90,
                food_group="tubérculos",
            ),
        ]

        selection = select_meal_food_candidates(
            foods=foods,
            preferred_terms=["pavo"],
            include_vegetable=False,
        )

        self.assertEqual(selection.protein_id, 2)

    def test_classification_keeps_high_fat_food_out_of_carb_role(self):
        almond_butter = NutritionFoodCandidate(
            food_id=1,
            name="Mantequilla de maní",
            protein=25,
            carbs=20,
            fat=50,
            kcal_per_100g=630,
            food_group="frutos secos",
        )

        carb_score, _ = classify_food_for_role(food=almond_butter, role="carb")
        fat_score, _ = classify_food_for_role(food=almond_butter, role="fat")

        self.assertGreater(fat_score, carb_score)

    def test_dailyplan_generator_uses_candidate_selector_boundary(self):
        foods = [
            DailyPlanGeneratorFood(
                food_id=10,
                name="Pollo",
                protein=31,
                carbs=0,
                fat=3,
                kcal_per_100g=151,
                food_group="carnes",
            ),
            DailyPlanGeneratorFood(
                food_id=11,
                name="Arroz",
                protein=2,
                carbs=28,
                fat=0.2,
                kcal_per_100g=122,
                food_group="cereales",
            ),
            DailyPlanGeneratorFood(
                food_id=12,
                name="Avena",
                protein=13,
                carbs=60,
                fat=7,
                kcal_per_100g=355,
                food_group="cereales",
            ),
        ]

        snack_template = next(
            template
            for template in build_dailyplan_meal_templates(4)
            if template.kind == "snack"
        )
        selection = _select_foods_for_meal(
            foods=foods,
            excluded_terms=["arroz"],
            preferred_terms=[],
            soft_avoid_ids=set(),
            template=snack_template,
        )

        self.assertEqual(selection.protein_id, 10)
        self.assertEqual(selection.carb_id, 12)
        self.assertEqual(DAILYPLAN_GENERATOR_VERSION, "nutrition_engine_v7_optimizer_gate")

    def test_missing_required_role_raises_selection_error(self):
        foods = [
            NutritionFoodCandidate(
                food_id=1,
                name="Aceite de oliva",
                protein=0,
                carbs=0,
                fat=100,
                kcal_per_100g=900,
                food_group="aceites",
            )
        ]

        with self.assertRaises(CandidateSelectionError):
            select_meal_food_candidates(foods=foods)
