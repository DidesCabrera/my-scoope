from dataclasses import replace

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from notas.application.ai_intake.dailyplan_generator import (
    generate_dailyplan_proposal_from_brief_proposal,
)
from notas.application.ai_intake.nutrition_brief import NutritionBrief
from notas.application.ai_intake.program_generator import create_weekly_program_proposal
from notas.application.ai_intake.proposal_from_brief import create_nutrition_brief_proposal
from notas.application.culinary_starter import seed_starter_library
from notas.application.proposals.solver_meal_proposals import create_solver_generated_meal_proposal
from notas.application.proposals.weekly_program import apply_approved_program_proposal
from notas.application.services.commands.proposal_commands import (
    apply_approved_create_dailyplan_proposal,
    apply_approved_create_meal_proposal,
    approve_proposal,
)
from notas.domain.models import CulinaryVariant, DailyPlan, Food, NutritionProposal

FOODS = (
    ("Yogur griego natural sin azúcar", 10, 4, 0.4, "ready_to_eat"),
    ("Avena tradicional", 13, 60, 7, "dry"),
    ("Leche descremada", 3.4, 5, 0.1, "ready_to_eat"),
    ("Clara de huevo", 11, 0.7, 0.2, "raw"),
    ("Huevo entero", 13, 1, 10, "raw"),
    ("Manzana", 0.3, 14, 0.2, "raw"),
    ("Plátano", 1.1, 23, 0.3, "raw"),
    ("Naranja cruda", 0.9, 12, 0.1, "raw"),
    ("Arroz blanco cocido", 2.7, 28, 0.3, "cooked"),
    ("Pechuga de pollo cocida", 31, 0, 3.6, "cooked"),
    ("Brócoli cocido", 2.4, 7, 0.4, "cooked"),
    ("Papa cocida sin piel", 2, 20, 0.1, "cooked"),
    ("Zanahoria cruda", 0.9, 10, 0.2, "raw"),
    ("Aceite de oliva", 0, 0, 100, "ready_to_eat"),
)


@override_settings(
    NUTRITION_CULINARY_PRIMARY_ENABLED=True,
    NUTRITION_CULINARY_RAW_FALLBACK_ENABLED=False,
    NUTRITION_SOLVER_TIME_LIMIT_MS=3000,
    NUTRITION_SOLVER_ALTERNATIVE_COUNT=2,
)
class CulinaryPrimaryGenerationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="culinary-primary")
        for name, protein, carbs, fat, preparation_state in FOODS:
            Food.objects.create(
                name=name,
                protein=protein,
                carbs=carbs,
                fat=fat,
                preparation_state=preparation_state,
                created_by=cls.user,
                solver_enabled=True,
                visibility=Food.VISIBILITY_CORE,
            )
        seed_starter_library(user=cls.user)

    def brief(self):
        return NutritionBrief(
            raw_prompt="Plan diario culinario",
            requested_entity="daily_plan",
            meals_per_day=4,
            calorie_target=2300,
            protein_target=145,
            carb_target=285,
            fat_target=65,
            weight_kg=80,
            dietary_pattern="omnivore",
        )

    def test_dailyplan_selects_validated_meals_before_adjusting_portions(self):
        source = create_nutrition_brief_proposal(user=self.user, brief=self.brief()).proposal
        generated = generate_dailyplan_proposal_from_brief_proposal(
            user=self.user,
            source_proposal=source,
            source=NutritionProposal.SOURCE_SYSTEM,
        ).proposal

        solver = generated.current_snapshot["nutrition_solver"]
        self.assertEqual(solver["active_backend"], "culinary_variants_cp_sat_v1")
        self.assertFalse(solver["raw_food_fallback_used"])
        self.assertEqual(len(solver["culinary_selections"]), 4)
        self.assertTrue(any(
            component["course"] == "dessert"
            for selection in solver["culinary_selections"]
            for component in selection["components"]
        ))
        self.assertEqual(len(generated.proposed_payload["dailyplan"]["meals"]), 4)

        approve_proposal(user=self.user, proposal=generated)
        applied = apply_approved_create_dailyplan_proposal(user=self.user, proposal=generated)
        self.assertEqual(applied.dailyplan.dailyplan_meals.count(), 4)

    def test_culinary_evidence_is_rechecked_before_dailyplan_apply(self):
        source = create_nutrition_brief_proposal(user=self.user, brief=self.brief()).proposal
        generated = generate_dailyplan_proposal_from_brief_proposal(
            user=self.user,
            source_proposal=source,
        ).proposal
        approve_proposal(user=self.user, proposal=generated)
        food = Food.objects.get(name="Avena tradicional")
        food.protein += 1
        food.save(update_fields=["protein"])

        with self.assertRaisesMessage(ValueError, "culinary_catalog_changed_since_review"):
            apply_approved_create_dailyplan_proposal(user=self.user, proposal=generated)
        self.assertFalse(DailyPlan.objects.filter(created_by=self.user).exists())

    def test_meal_proposal_uses_a_validated_variant_and_preserves_courses(self):
        context = DailyPlan.objects.create(name="Contexto", created_by=self.user)
        result = create_solver_generated_meal_proposal(
            user=self.user,
            dailyplan_id=context.pk,
            title="Almuerzo culinario",
            target={"kcal": 650, "protein": 50, "carbs": 75, "fat": 17},
            meal_slot="Almuerzo",
        )

        summary = result.proposal.validation_summary["nutrition_solver"]
        self.assertEqual(summary["source_boundary"]["candidate_source"], "notas.CulinaryVariant")
        self.assertFalse(summary["raw_food_fallback_used"])
        selection = result.proposal.current_snapshot["culinary_selection"][0]
        self.assertTrue(any(component["course"] == "dessert" for component in selection["components"]))
        approve_proposal(user=self.user, proposal=result.proposal)
        applied = apply_approved_create_meal_proposal(user=self.user, proposal=result.proposal)
        self.assertEqual(applied.meal.meal_food_set.count(), len(selection["foods"]))

    def test_catalog_contains_multiple_rule_validated_options_per_supported_kind(self):
        by_kind = {kind: set() for kind in ("breakfast", "main", "snack", "dinner")}
        for variant in CulinaryVariant.objects.select_related("template"):
            for kind in variant.template.meal_kinds:
                by_kind[kind].add(variant.template.family)
        self.assertTrue(all(len(families) >= 2 for families in by_kind.values()), by_kind)
        orange = Food.objects.get(name="Naranja cruda")
        self.assertTrue(any(
            any(row["food_id"] == orange.pk and row["component"] == "dessert" for row in variant.ingredients)
            for variant in CulinaryVariant.objects.select_related("template")
            if "main" in variant.template.meal_kinds
        ))

    def test_program_without_typed_weekly_spec_reuses_culinary_daily_menus(self):
        brief = self.brief()
        program_brief = replace(brief, requested_entity="program", duration_weeks=1)
        proposal = create_weekly_program_proposal(user=self.user, brief=program_brief)

        self.assertEqual(proposal.current_snapshot["generator_backend"], "culinary_variants_cp_sat_v1")
        self.assertEqual(len(proposal.current_snapshot["culinary_selections"]), 28)
        approve_proposal(user=self.user, proposal=proposal)
        applied = apply_approved_program_proposal(user=self.user, proposal=proposal)
        self.assertEqual(applied.program.program_dailyplan.count(), 7)
