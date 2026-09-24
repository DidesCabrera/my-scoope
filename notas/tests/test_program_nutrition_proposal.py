from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from notas.application.ai_intake.nutrition_brief import NutritionBrief, deserialize_brief, serialize_brief
from notas.application.ai_intake.program_generator import create_weekly_program_proposal
from notas.application.ai_tools.proposal_tools import build_nutrition_brief_from_ai_drafts
from notas.application.dto.program_proposal import parse_program_payload
from notas.application.proposals.weekly_program import apply_approved_program_proposal
from notas.application.queries.proposal_simulation_queries import simulate_proposal_payload
from notas.domain.models import DailyPlan, Food, Meal, NutritionProposal, Program, ProgramDay


class ProgramNutritionProposalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="weekly")
        self.other = User.objects.create_user(username="other-weekly")
        self.food = Food.objects.create(name="Ingrediente", created_by=self.user, protein=20, carbs=30, fat=10)

    def payload(self, weeks=1):
        return {"intent": "create_program", "program": {"name": "Programa", "duration_weeks": weeks, "days": [
            {"week_number": week, "day_number": day, "dailyplan": {"name": f"Semana {week} Día {day}", "meals": [
                {"hour": "13:00", "note": "", "meal": {"name": "Almuerzo", "foods": [{"food_id": self.food.pk, "quantity": 100, "unit": "g"}]}}
            ]}} for week in range(1, weeks + 1) for day in range(1, 8)
        ]}}

    def proposal(self, weeks=1):
        payload = self.payload(weeks)
        return NutritionProposal.objects.create(created_by=self.user, title="Programa", status=NutritionProposal.STATUS_APPROVED,
            proposed_payload=payload, validation_summary={"simulation": simulate_proposal_payload(self.user, payload).as_dict()})

    def test_one_to_eight_complete_weeks_roundtrip(self):
        for weeks in range(1, 9):
            with self.subTest(weeks=weeks):
                parsed = parse_program_payload(self.payload(weeks))
                self.assertEqual(len(parsed.days), weeks * 7)
                self.assertEqual(parsed.as_dict(), self.payload(weeks))

    def test_incomplete_duplicate_and_out_of_range_slots_are_rejected(self):
        for mode in ("missing", "duplicate", "week", "day", "bool"):
            payload = self.payload(8)
            if mode == "missing":
                payload["program"]["days"].pop()
            elif mode == "duplicate":
                payload["program"]["days"][-1] = deepcopy(payload["program"]["days"][0])
            else:
                payload["program"]["days"][0]["week_number" if mode == "week" else "day_number"] = True if mode == "bool" else 9
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                parse_program_payload(payload)

    def test_invalid_duration_not_silently_truncated(self):
        for duration in (0, 9, -1, True, "8", 1.5):
            payload = self.payload()
            payload["program"]["duration_weeks"] = duration
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                parse_program_payload(payload)
            with self.assertRaises(ValueError):
                deserialize_brief({"raw_prompt": "programa", "duration_weeks": duration})

    def test_eight_week_apply_creates_56_independent_snapshots(self):
        proposal = self.proposal(8)
        result = apply_approved_program_proposal(user=self.user, proposal=proposal)
        slots = list(ProgramDay.objects.filter(program=result.program).select_related("dailyplan"))
        self.assertEqual(len(slots), 56)
        self.assertEqual(len({slot.dailyplan_id for slot in slots}), 56)
        self.assertEqual(DailyPlan.objects.filter(source=DailyPlan.SOURCE_PROGRAM).count(), 56)
        self.assertEqual(Meal.objects.count(), 56)
        self.assertEqual(result.program.duration_weeks, 8)
        slots[0].dailyplan.name = "Cambio individual"
        slots[0].dailyplan.save()
        slots[1].dailyplan.refresh_from_db()
        self.assertNotEqual(slots[1].dailyplan.name, "Cambio individual")
        with self.assertRaisesMessage(ValueError, "proposal_apply_requires_applicable_status"):
            apply_approved_program_proposal(user=self.user, proposal=proposal)
        self.assertEqual(Program.objects.count(), 1)

    def test_owner_approval_and_stale_evidence_block_all_writes(self):
        proposal = self.proposal()
        with self.assertRaises(ValueError):
            apply_approved_program_proposal(user=self.other, proposal=proposal)
        proposal.status = NutritionProposal.STATUS_PENDING_REVIEW
        proposal.save()
        with self.assertRaises(ValueError):
            apply_approved_program_proposal(user=self.user, proposal=proposal)
        proposal.status = NutritionProposal.STATUS_APPROVED
        proposal.save()
        self.food.protein = 40
        self.food.save()
        with self.assertRaisesMessage(ValueError, "program_proposal_changed_since_review"):
            apply_approved_program_proposal(user=self.user, proposal=proposal)
        self.assertEqual(Program.objects.count(), 0)
        self.assertEqual(DailyPlan.objects.count(), 0)

    def test_late_failure_rolls_back_entire_program(self):
        proposal = self.proposal()
        original = ProgramDay.objects.create
        calls = 0

        def fail_later(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise ValueError("simulated_storage_failure")
            return original(**kwargs)

        with patch("notas.application.proposals.weekly_program.ProgramDay.objects.create", side_effect=fail_later):
            with self.assertRaises(ValueError):
                apply_approved_program_proposal(user=self.user, proposal=proposal)
        self.assertEqual(Program.objects.count(), 0)
        self.assertEqual(DailyPlan.objects.count(), 0)
        self.assertEqual(Meal.objects.count(), 0)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPROVED)

    def test_typed_requirements_and_duration_survive_drafts(self):
        from notas.application.ai_intake.brief_tool_updates import apply_proposal_preferences_to_brief
        brief = build_nutrition_brief_from_ai_drafts(profile_draft={},
            proposal_preferences={"requested_entity": "program", "duration_weeks": 8},
            preference_draft={"dietary_pattern": "vegetarian", "allergies_or_intolerances": ["peanut"], "variety_preference": "high"})
        self.assertEqual(deserialize_brief(serialize_brief(brief)).duration_weeks, 8)
        self.assertEqual(brief.dietary_pattern, "vegetarian")
        self.assertEqual(brief.allergies_or_intolerances, ["peanut"])
        self.assertEqual(brief.variety_preference, "high")
        updated = apply_proposal_preferences_to_brief(NutritionBrief(raw_prompt=""), {"requested_entity": "program", "duration_weeks": 8})
        self.assertEqual(updated.duration_weeks, 8)

    def test_mobile_contract_and_web_review_expose_last_day(self):
        from mobile_api.schema_domains.proposals import ProposalDetailData
        from mobile_api.selectors_proposals import proposal_detail_payload
        from nutrition_solver.application.program_specification import parse_program_specification
        from nutrition_solver.tests.test_program_specification import example_spec
        proposal = self.proposal(8)
        proposal.targets = {"program_specification": parse_program_specification(example_spec(8)).as_dict()}
        proposal.save(update_fields=["targets"])
        payload = proposal_detail_payload(self.user, proposal.pk)
        parsed = ProposalDetailData.model_validate(payload)
        self.assertEqual(parsed.attachment_kind, "program")
        self.assertEqual(len(parsed.program.days), 56)
        self.assertEqual(parsed.program.days[-1].week_number, 8)
        self.assertEqual(parsed.program.days[-1].day_number, 7)
        self.client.force_login(self.user)
        program_url = reverse("proposal_program_detail", args=[proposal.pk])
        with self.settings(NUTRITION_ONBOARDING_GATE_ENABLED=False):
            response = self.client.get(reverse("proposal_detail", args=[proposal.pk]))
            program_response = self.client.get(program_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, program_url)
        self.assertContains(response, "program-card")
        self.assertNotContains(response, "program-week-tabs")
        self.assertNotContains(response, "proposal-review-intent-line")
        self.assertContains(response, "Parámetros usados para construir y validar la propuesta")
        self.assertContains(response, "Energía diaria")
        self.assertContains(response, "2500 → 1700 kcal")
        self.assertContains(response, "Peso de referencia")
        proposal_html = response.content.decode()
        self.assertLess(proposal_html.index("</header>"), proposal_html.index("proposal-program-objectives"))
        self.assertLess(proposal_html.index("proposal-program-objectives"), proposal_html.index("proposal-attachment--program"))
        self.assertLess(proposal_html.index("proposal-attachment--program"), proposal_html.index('class="card card--program program-card"'))
        self.assertContains(program_response, "Semana 8")
        self.assertContains(program_response, "program-chart-panel")
        self.assertContains(program_response, "program-week-tabs")
        self.assertContains(program_response, "Tabla de comparación entre planes diarios")
        self.assertContains(program_response, "program-week-foods-aggregation")
        self.assertContains(program_response, "proposal-program-week-8-day-7-card")
        self.assertNotContains(program_response, "proposal-program-objectives")
        self.assertContains(program_response, "Ingrediente (100g)")
        self.assertNotContains(response, "program_specification")
        self.assertNotContains(response, "protein_max_g")
        self.assertNotContains(response, '<details class="proposal-review-card">')
        proposal.targets = {}
        proposal.save(update_fields=["targets"])
        apply_approved_program_proposal(user=self.user, proposal=proposal)
        result = ProposalDetailData.model_validate(proposal_detail_payload(self.user, proposal.pk))
        self.assertEqual(result.applied_result.kind, "program")

    def test_web_program_proposal_supports_dailyplan_meal_and_food_navigation(self):
        proposal = self.proposal(2)
        proposal.validation_summary["simulation"]["program"]["days"][-1]["dailyplan"]["meals"][0]["note"] = "Nota solo en detalle"
        proposal.save(update_fields=["validation_summary"])
        self.client.force_login(self.user)
        program_url = reverse("proposal_program_detail", args=[proposal.pk])
        routes = [
            reverse("proposal_program_dailyplan_detail", args=[proposal.pk, 2, 7]),
            reverse("proposal_program_meal_detail", args=[proposal.pk, 2, 7, 1]),
            reverse("proposal_program_food_detail", args=[proposal.pk, 2, 7, 1, 1]),
        ]

        with self.settings(NUTRITION_ONBOARDING_GATE_ENABLED=False):
            proposal_response = self.client.get(reverse("proposal_detail", args=[proposal.pk]))
            program_response = self.client.get(program_url)
            responses = [self.client.get(url) for url in routes]
            missing_response = self.client.get(
                reverse("proposal_program_food_detail", args=[proposal.pk, 2, 7, 1, 2])
            )

        self.assertContains(proposal_response, program_url)
        self.assertContains(program_response, routes[0])
        self.assertEqual([response.status_code for response in responses], [200, 200, 200])
        self.assertContains(responses[0], "Comidas de este plan")
        self.assertContains(responses[0], routes[1])
        self.assertContains(responses[0], "structural-item--time")
        self.assertContains(responses[0], "13:00")
        self.assertNotContains(responses[0], "Nota solo en detalle")
        self.assertContains(responses[1], "Detalle de cada Alimento")
        self.assertContains(responses[1], routes[2])
        self.assertContains(responses[1], "Nota solo en detalle")
        self.assertContains(responses[2], "Alimento dentro de la propuesta")
        self.assertContains(responses[2], "Ingrediente")
        self.assertEqual(missing_response.status_code, 404)

    def test_inactive_ingredient_cannot_be_applied(self):
        proposal = self.proposal()
        self.food.is_active = False
        self.food.save()
        with self.assertRaisesMessage(ValueError, "proposal_apply_food_not_available"):
            apply_approved_program_proposal(user=self.user, proposal=proposal)
        self.assertEqual(Program.objects.count(), 0)

    def test_generation_does_not_create_program_or_plans(self):
        daily = {"intent": "create_dailyplan", "dailyplan": self.payload()["program"]["days"][0]["dailyplan"]}
        validation = {"target_comparison": {}, "engine_validation": {"is_valid": True, "has_errors": False}}
        brief = NutritionBrief(raw_prompt="8 semanas", requested_entity="program", duration_weeks=8, meals_per_day=1,
            calorie_target=2000, protein_target=150, carb_target=200, fat_target=66)
        with patch("notas.application.ai_intake.program_generator._build_dailyplan_payload_with_solver_summary", return_value=(daily, {})), patch("notas.application.ai_intake.program_generator._build_validation_summary", return_value=validation):
            proposal = create_weekly_program_proposal(user=self.user, brief=brief)
        self.assertEqual(len(proposal.proposed_payload["program"]["days"]), 56)
        self.assertEqual(len(proposal.validation_summary["days"]), 56)
        self.assertEqual(proposal.validation_summary["variety"]["unique_daily_menus"], 1)
        self.assertEqual(proposal.status, NutritionProposal.STATUS_PENDING_REVIEW)
        self.assertEqual(Program.objects.count(), 0)
        self.assertEqual(DailyPlan.objects.count(), 0)

    def test_nonfinite_food_quantities_are_rejected(self):
        for quantity in (float("nan"), float("inf"), float("-inf")):
            payload = self.payload()
            payload["program"]["days"][0]["dailyplan"]["meals"][0]["meal"]["foods"][0]["quantity"] = quantity
            with self.assertRaises(ValueError):
                parse_program_payload(payload)

    def test_provider_summary_is_bounded_without_losing_duration(self):
        import json

        from notas.application.ai_intake.program_generator import program_proposal_tool_summary
        proposal = self.proposal(8)
        proposal.validation_summary.update(days=[{"engine_validation": {}}] * 56,
            payload_validation={"is_valid": True}, variety={"unique_daily_menus": 1, "repeated_menus": True})
        summary = program_proposal_tool_summary(proposal)
        self.assertEqual(summary["proposed_payload"]["program"]["day_count"], 56)
        self.assertEqual(summary["proposed_payload"]["program"]["duration_weeks"], 8)
        self.assertLess(len(json.dumps(summary)), 2500)
