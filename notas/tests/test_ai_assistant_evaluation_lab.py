from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from ai_assistant.models import AIUsageEvent
from notas.application.ai_intake.evaluation_lab import (
    EVALUATION_LAB_VERSION,
    _build_diagnostics,
    _credit_block_reasons,
    run_evaluation_lab,
)
from notas.application.ai_intake.real_provider_validation import (
    RealProviderValidationReport,
)
from notas.domain.models import Food, Meal, MealFood


class AIAssistantEvaluationLabTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="evaluation-lab-user",
            email="evaluation-lab@example.com",
            password="not-used",
        )

    def test_deterministic_preflight_uses_canonical_library_truth_without_provider_calls(self):
        Food.objects.create(
            name="Alimento visible",
            protein=10,
            carbs=20,
            fat=5,
            created_by=self.user,
        )

        report = run_evaluation_lab(
            user=self.user,
            scenario_keys=("bibliotecas_coherentes",),
        )

        self.assertEqual(report.status, "preflight_ready")
        self.assertEqual(EVALUATION_LAB_VERSION, "ai_assistant.evaluation_lab.v2")
        self.assertTrue(report.passed)
        self.assertEqual(report.ground_truth["libraries"]["foods"], 1)
        self.assertEqual(report.catalog["total_capabilities"], 82)
        self.assertEqual(
            report.catalog["mapped_capability_ids"],
            ["DP-01", "F-01", "M-01", "PG-01"],
        )
        self.assertIsNone(report.live_validation)
        self.assertEqual(report.live_validations, ())
        self.assertEqual(report.quality_evaluation["status"], "not_run")
        self.assertTrue(report.task_dataset["passed"])
        self.assertEqual(report.task_dataset["case_count"], 64)
        self.assertEqual(report.product_feedback["scope"], "selected_user")
        self.assertEqual(AIUsageEvent.objects.count(), 0)

    def test_preflight_separates_missing_catalog_data_from_model_behavior(self):
        report = run_evaluation_lab(
            user=self.user,
            scenario_keys=("comida_450_kcal",),
        )

        self.assertEqual(report.status, "blocked_by_fixture")
        item = report.scenario_preflight[0]
        self.assertEqual(item["status"], "blocked_by_fixture")
        self.assertEqual(
            {failure["requirement"] for failure in item["failures"]},
            {"owned_dailyplan", "solver_450_feasible"},
        )
        self.assertIn("catalog_data", report.diagnostics["failed_domains"])
        self.assertIn("solver_feasibility", report.diagnostics["failed_domains"])
        self.assertEqual(AIUsageEvent.objects.count(), 0)

    def test_replacement_scenario_binds_exact_database_entities(self):
        source = Food.objects.create(
            name="Arroz ensayo",
            protein=3,
            carbs=28,
            fat=1,
            created_by=self.user,
        )
        replacement = Food.objects.create(
            name="Papa ensayo",
            protein=2,
            carbs=20,
            fat=0.2,
            created_by=self.user,
        )
        meal = Meal.objects.create(
            name="Almuerzo ensayo",
            created_by=self.user,
            is_draft=False,
        )
        MealFood.objects.create(meal=meal, food=source, quantity=100)

        report = run_evaluation_lab(
            user=self.user,
            scenario_keys=("reemplazo_alimento_200g",),
        )

        self.assertEqual(report.status, "preflight_ready")
        item = report.scenario_preflight[0]
        self.assertEqual(item["status"], "ready")
        self.assertEqual(item["ground_truth"]["meal_id"], meal.id)
        self.assertEqual(item["ground_truth"]["source_food_id"], source.id)
        self.assertEqual(item["ground_truth"]["replacement_food_id"], replacement.id)
        self.assertEqual(item["ground_truth"]["target_quantity_g"], 200)

    def test_command_lists_lab_scenarios_without_user_or_provider(self):
        output = StringIO()

        call_command("evaluate_ai_assistant_lab", list_scenarios=True, stdout=output)

        text = output.getvalue()
        self.assertIn("bibliotecas_coherentes", text)
        self.assertIn("comida_450_kcal", text)
        self.assertIn("M-08", text)

    @override_settings(AI_ASSISTANT_CREDITS_ENABLED=True)
    def test_live_lab_is_unmetered_by_default_but_can_opt_in_to_user_credits(self):
        observed_credit_settings = []

        def fake_live_report(**kwargs):
            observed_credit_settings.append(settings.AI_ASSISTANT_CREDITS_ENABLED)
            return RealProviderValidationReport(
                version="test",
                run_id=kwargs["run_id"],
                provider="openai",
                model="test-model",
                user_id=self.user.id,
                configured_chat_mode="llm",
                usage_observability_enabled=True,
                credits_enabled=settings.AI_ASSISTANT_CREDITS_ENABLED,
                scenarios=(),
                usage_summary={},
                credit_summary={},
                manual_review_prompts=(),
            )

        target = "notas.application.ai_intake.evaluation_lab.run_real_provider_validation"
        with patch(target, side_effect=fake_live_report):
            unmetered = run_evaluation_lab(
                user=self.user,
                scenario_keys=("bibliotecas_coherentes",),
                live=True,
            )
            metered = run_evaluation_lab(
                user=self.user,
                scenario_keys=("bibliotecas_coherentes",),
                live=True,
                charge_user_credits=True,
            )

        self.assertEqual(observed_credit_settings, [False, True])
        self.assertEqual(unmetered.billing["policy"], "internal_unmetered")
        self.assertFalse(unmetered.billing["user_credits_charged"])
        self.assertEqual(metered.billing["policy"], "charge_selected_user")
        self.assertTrue(metered.billing["user_credits_charged"])

    def test_credit_block_is_reported_as_infrastructure_not_tool_regressions(self):
        result = SimpleNamespace(
            scenario=SimpleNamespace(key="comida_450_kcal"),
            turns=(
                SimpleNamespace(
                    usage_observability={"error_type": "daily_credit_limit_exceeded"},
                    tool_results=(),
                ),
            ),
            checks=(
                SimpleNamespace(
                    key="tool_contract",
                    passed=False,
                    severity="hard",
                    detail="missing solver tool",
                ),
            ),
        )
        live_report = SimpleNamespace(scenarios=(result,))

        diagnostics = _build_diagnostics(preflight=(), live_report=live_report)

        self.assertEqual(_credit_block_reasons(live_report), ["daily_credit_limit_exceeded"])
        self.assertEqual(diagnostics["failed_domains"], ["credit_quota"])
        self.assertNotIn("tool_routing", diagnostics["by_domain"])
