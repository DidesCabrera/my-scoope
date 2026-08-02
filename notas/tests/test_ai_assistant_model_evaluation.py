from __future__ import annotations

from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from ai_assistant.application.chat_engines import ChatEngineTurnResult
from ai_assistant.models import AIUsageEvent
from notas.application.ai_intake.model_evaluation import (
    AIModelEvaluationCandidate,
    configured_model_evaluation_candidates,
    evaluate_ai_assistant_models,
)
from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    NutritionConversationMessage,
    NutritionConversationState,
    build_llm_intake_result_from_brief,
)


class ScriptedSimpleValidationEngine:
    engine_name = "scripted_model_eval_engine"

    def continue_chat(self, request):
        assistant = "Claro. Te ayudo a ordenar tu alimentacion con una propuesta concreta."
        messages = [
            NutritionConversationMessage(role="user", text=request.normalized_message),
            NutritionConversationMessage(role="assistant", text=assistant),
        ]
        AIUsageEvent.objects.create(
            user=request.metadata["tool_user"],
            period="2026-07",
            conversation_id=request.metadata["conversation_id"],
            turn_id=request.metadata["turn_id"],
            action_type=request.metadata["action_type"],
            provider=settings.AI_ASSISTANT_LLM_PROVIDER,
            model_name=settings.AI_ASSISTANT_OPENAI_MODEL,
            input_tokens=100,
            cached_input_tokens=10,
            output_tokens=40,
            total_tokens=140,
            estimated_cost_usd="0.000330",
            status=AIUsageEvent.Status.COMPLETED,
            tool_calls_count=0,
        )
        state = NutritionConversationState(
            messages=messages,
            result=build_llm_intake_result_from_brief(
                NutritionBrief(raw_prompt=request.normalized_message)
            ),
        )
        return ChatEngineTurnResult(
            state=state,
            assistant_text=assistant,
            is_ready_for_proposal=False,
            engine_name=self.engine_name,
            metadata={
                "llm_provider": settings.AI_ASSISTANT_LLM_PROVIDER,
                "llm_model": settings.AI_ASSISTANT_OPENAI_MODEL,
                "llm_semantic_intent": "answer_question",
                "llm_semantic_missing_slots": (),
                "llm_tool_results": (),
                "llm_provider_native_tool_transport": False,
                "llm_provider_native_tool_calls": 0,
                "llm_degraded": False,
                "deterministic_runtime_invoked": False,
                "usage_observability": {"recorded": True, "status": "completed"},
            },
        )


@override_settings(
    AI_ASSISTANT_LLM_PROVIDER="openai",
    AI_ASSISTANT_OPENAI_MODEL="gpt-5.6-luna",
    AI_ASSISTANT_OPENAI_REASONING_EFFORT="low",
    AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=True,
    AI_ASSISTANT_CREDITS_ENABLED=False,
    AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS=True,
)
class AIAssistantModelEvaluationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="model-eval-user",
            email="model-eval@example.com",
            password="not-used",
        )

    def test_configured_candidates_skip_sol_benchmark_by_default(self):
        candidates = configured_model_evaluation_candidates()
        codes = [candidate.code for candidate in candidates]

        self.assertIn("luna_low", codes)
        self.assertIn("terra_low", codes)
        self.assertNotIn("sol_medium", codes)

        benchmark_codes = [
            candidate.code
            for candidate in configured_model_evaluation_candidates(include_benchmarks=True)
        ]
        self.assertIn("sol_medium", benchmark_codes)

    def test_evaluation_accepts_luna_baseline_when_hard_checks_pass(self):
        original_model = settings.AI_ASSISTANT_OPENAI_MODEL
        candidates = (
            AIModelEvaluationCandidate(
                code="luna_low",
                provider="openai",
                model="gpt-5.6-luna",
                reasoning_effort="low",
                max_output_tokens=1800,
                role="baseline",
            ),
            AIModelEvaluationCandidate(
                code="terra_low",
                provider="openai",
                model="gpt-5.6-terra",
                reasoning_effort="low",
                max_output_tokens=2000,
                role="escalation",
            ),
        )

        report = evaluate_ai_assistant_models(
            user=self.user,
            candidates=candidates,
            scenario_keys=("saludo_y_descubrimiento",),
            run_id="unit-model-eval",
            engine_factory=lambda candidate: ScriptedSimpleValidationEngine(),
        )

        self.assertTrue(report.passed)
        self.assertEqual(report.recommendation["accepted_candidate"], "luna_low")
        self.assertEqual(report.recommendation["decision"], "accept_baseline")
        self.assertEqual(len(report.results), 2)
        self.assertEqual(report.results[0].quality_summary["passed_scenarios"], 1)
        self.assertEqual(report.results[0].cost_summary["estimated_cost_usd"], "0.000330")
        self.assertEqual(settings.AI_ASSISTANT_OPENAI_MODEL, original_model)

    def test_management_command_requires_live_confirmation(self):
        with self.assertRaisesMessage(CommandError, "Model evaluation makes real provider calls"):
            call_command(
                "evaluate_ai_assistant_models",
                user_id=self.user.id,
                stdout=StringIO(),
            )

    def test_management_command_lists_candidates_without_provider_calls(self):
        output = StringIO()
        call_command(
            "evaluate_ai_assistant_models",
            list_candidates=True,
            stdout=output,
        )

        self.assertIn("luna_low", output.getvalue())
        self.assertIn("terra_low", output.getvalue())
        self.assertIn("sol_medium", output.getvalue())
