from copy import deepcopy

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from notas.application.ai_intake.culinary_program import build_culinary_program, revalidate_culinary_proposal
from notas.application.ai_intake.nutrition_brief import NutritionBrief, deserialize_brief, serialize_brief
from notas.application.culinary_library import load_culinary_candidates, validate_variant
from notas.application.culinary_starter import seed_starter_library
from notas.application.proposals.weekly_program import apply_approved_program_proposal
from notas.domain.models import CulinaryVariant, Food, Meal, NutritionProposal, Program, WeightLog
from nutrition_solver.tests.test_program_specification import example_spec

FOODS = (
    ("Yogur griego natural sin azúcar", 10, 4, .4, "ready_to_eat"),
    ("Avena tradicional", 13, 60, 7, "dry"), ("Manzana", .3, 14, .2, "raw"),
    ("Plátano", 1.1, 23, .3, "raw"), ("Arándanos", .7, 14, .3, "raw"),
    ("Leche descremada", 3.4, 5, .1, "ready_to_eat"), ("Clara de huevo", 11, .7, .2, "raw"),
    ("Huevo entero", 13, 1, 10, "raw"), ("Arroz blanco cocido", 2.7, 28, .3, "cooked"),
    ("Arroz integral cocido", 2.6, 23, .9, "cooked"), ("Quinoa cocida", 4.4, 21, 1.9, "cooked"),
    ("Pechuga de pollo cocida", 31, 0, 3.6, "cooked"), ("Pechuga de pavo cocida", 29, 0, 2, "cooked"),
    ("Carne magra cocida", 28, 0, 7, "cooked"), ("Brócoli cocido", 2.4, 7, .4, "cooked"),
    ("Aceite de oliva", 0, 0, 100, "ready_to_eat"), ("Papa cocida sin piel", 2, 20, .1, "cooked"),
    ("Camote cocido", 1.6, 20, .1, "cooked"), ("Zanahoria cruda", .9, 10, .2, "raw"),
    ("Tomate", .9, 4, .2, "raw"), ("Atún en agua drenado", 25, 0, 1, "ready_to_eat"),
    ("Palta", 2, 9, 15, "raw"), ("Lentejas cocidas", 9, 20, .4, "cooked"),
    ("Porotos negros cocidos", 9, 24, .5, "cooked"), ("Garbanzos cocidos", 9, 27, 2.6, "cooked"),
)


class CulinaryProgramTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="culinary")
        cls.other = User.objects.create_user(username="other-culinary")
        for name, protein, carbs, fat, state in FOODS:
            Food.objects.create(name=name, protein=protein, carbs=carbs, fat=fat, preparation_state=state,
                                created_by=cls.user, solver_enabled=True, visibility="core")
        seed_starter_library(user=cls.user)

    def brief(self, weeks=1):
        return NutritionBrief(raw_prompt="Programa progresivo", requested_entity="program", duration_weeks=weeks,
                              meals_per_day=4, program_specification=example_spec(weeks))

    def test_library_private_idempotent_and_not_human_validated(self):
        self.assertGreater(CulinaryVariant.objects.count(), 20)
        self.assertEqual(seed_starter_library(user=self.user)["created"], 0)
        self.assertFalse(CulinaryVariant.objects.filter(status="human_validated").exists())
        self.assertEqual(load_culinary_candidates(user=self.other)[0], ())
        with self.assertRaises(ValueError):
            validate_variant(user=self.other, variant_id=CulinaryVariant.objects.first().pk)

    def test_candidate_names_fit_operational_meals_before_review(self):
        candidates, _ = load_culinary_candidates(user=self.user)
        limit = Meal._meta.get_field("name").max_length
        self.assertTrue(CulinaryVariant.objects.filter(name__regex=r".{101}").exists())
        self.assertTrue(all(len(candidate.name) <= limit for candidate in candidates))
        self.assertTrue(any(candidate.name.endswith("…") for candidate in candidates))

    def test_stale_foods_are_not_reused_and_variants_are_immutable(self):
        variant = CulinaryVariant.objects.first()
        variant.ingredients[0]["maximum_g"] = 9999
        with self.assertRaises(ValidationError):
            variant.save()
        food = Food.objects.get(name="Yogur griego natural sin azúcar")
        food.protein += 1
        food.save()
        _, rejected = load_culinary_candidates(user=self.user)
        self.assertTrue(any(item["reason"] == "culinary_evidence_stale" for item in rejected))

    def test_requirements_survive_brief_roundtrip(self):
        brief = deserialize_brief(serialize_brief(self.brief(8)))
        self.assertEqual(brief.program_specification["weeks"][-1]["protein_min_g"], 160)

    def test_tool_capture_preserves_spec_and_supersedes_scalar_targets(self):
        from notas.application.ai_intake.brief_tool_updates import apply_proposal_preferences_to_brief
        from notas.application.ai_tools.proposal_preference_tools import _update_proposal_preferences_data
        from notas.application.ai_tools.proposal_tools import build_nutrition_brief_from_ai_drafts
        response = _update_proposal_preferences_data(self.user, {"program_specification": example_spec()}, {"calorie_target": 2400})
        self.assertEqual(response["superseded_scalar_fields"], ["calorie_target"])
        brief = apply_proposal_preferences_to_brief(NutritionBrief(raw_prompt="", calorie_target=2400), response["proposal_preferences"])
        self.assertIsNone(brief.calorie_target)
        self.assertEqual(brief.duration_weeks, 8)
        composed = build_nutrition_brief_from_ai_drafts(profile_draft={}, proposal_preferences=response["proposal_preferences"])
        self.assertEqual(composed.program_specification["weeks"][-1]["protein_min_g"], 160)

    def test_partial_revision_and_inspection_preserve_unselected_meals(self):
        from notas.application.ai_intake.culinary_program import revise_culinary_program
        from notas.application.ai_tools.program_tools import inspect_program_proposal
        source = build_culinary_program(user=self.user, brief=self.brief())
        before = deepcopy(source.proposed_payload)
        revised = revise_culinary_program(user=self.user, proposal_id=source.pk, week_numbers=[1], meal_numbers=[4])
        for old, new in zip(before["program"]["days"], revised.proposed_payload["program"]["days"]):
            self.assertEqual(old["dailyplan"]["meals"][:3], new["dailyplan"]["meals"][:3])
            self.assertNotEqual(old["dailyplan"]["meals"][3], new["dailyplan"]["meals"][3])
        source.refresh_from_db()
        self.assertEqual(source.proposed_payload, before)
        self.assertEqual(revised.status, NutritionProposal.STATUS_PENDING_REVIEW)
        detail = inspect_program_proposal(self.user, revised.pk, week_number=1, day_number=2)
        self.assertEqual(len(detail["proposal"]["days"]), 1)
        with self.assertRaises(ValueError):
            inspect_program_proposal(self.other, revised.pk, week_number=1)

    def test_payload_tampering_is_rejected_even_with_updated_simulation(self):
        from notas.application.queries.proposal_simulation_queries import simulate_proposal_payload
        proposal = build_culinary_program(user=self.user, brief=self.brief())
        proposal.proposed_payload["program"]["days"][0]["dailyplan"]["meals"][0]["meal"]["foods"][0]["quantity"] = 900
        proposal.validation_summary["simulation"] = simulate_proposal_payload(self.user, proposal.proposed_payload).as_dict()
        proposal.status = NutritionProposal.STATUS_APPROVED
        proposal.save()
        with self.assertRaises(ValueError):
            apply_approved_program_proposal(user=self.user, proposal=proposal)
        self.assertEqual(Program.objects.count(), 0)

    def test_one_week_generated_validated_and_applied(self):
        proposal = build_culinary_program(user=self.user, brief=self.brief())
        validation = revalidate_culinary_proposal(user=self.user, proposal=proposal)
        self.assertTrue(validation["valid"])
        self.assertEqual(len(validation["days"]), 7)
        self.assertEqual(Program.objects.count(), 0)
        proposal.status = NutritionProposal.STATUS_APPROVED
        proposal.save()
        result = apply_approved_program_proposal(user=self.user, proposal=proposal)
        self.assertEqual(result.program.program_dailyplan.count(), 7)
        self.assertEqual(result.program.nutrition_specification["weeks"][0]["kcal"], 2500)

    def test_eight_week_progression_all_56_days(self):
        proposal = build_culinary_program(user=self.user, brief=self.brief(8))
        validation = revalidate_culinary_proposal(user=self.user, proposal=proposal)
        self.assertTrue(validation["valid"])
        self.assertEqual(len(validation["days"]), 56)
        means = validation["weekly_mean_kcal"]
        self.assertTrue(all(left > right for left, right in zip(means, means[1:])))
        self.assertTrue(all(day["fat_percent"] <= 25 and 2 <= day["ppk"] <= 2.2 for day in validation["days"]))
        self.assertEqual(proposal.status, NutritionProposal.STATUS_PENDING_REVIEW)

    @override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
    def test_manual_configuration_is_owner_only_and_does_not_modify_weight(self):
        program = Program.objects.create(name="Programa", created_by=self.user, duration_weeks=1)
        url = reverse("program_nutrition_settings", args=[program.pk])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.user)
        self.assertContains(self.client.get(url), "Peso proyectado")
        spec = example_spec(1)
        data = {k: v for k, v in spec.items() if k not in {"version", "duration_weeks", "weeks", "energy_source"}}
        data.update({"weeks-TOTAL_FORMS": "1", "weeks-INITIAL_FORMS": "1", "weeks-MIN_NUM_FORMS": "1", "weeks-MAX_NUM_FORMS": "1",
                     "weeks-0-kcal": "2500", "weeks-0-projected_weight_kg": "85", "action": "save"})
        before = WeightLog.objects.count()
        self.assertEqual(self.client.post(url, data).status_code, 302)
        program.refresh_from_db()
        self.assertTrue(program.culinary_provenance["needs_revalidation"])
        self.assertEqual(WeightLog.objects.count(), before)
