from decimal import Decimal

from django.test import SimpleTestCase, TestCase, override_settings

from ai_assistant.application.usage import (
    ACTION_ASSISTANT_CHAT,
    ACTION_CREATE_MEAL_PROPOSAL,
    aggregate_provider_usage,
    estimate_cost_usd,
    infer_action_type,
)
from ai_assistant.domain import (
    AssistantIntent,
    AssistantIntentName,
    AssistantMessage,
    AssistantMessageRole,
    AssistantStructuredResponse,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers import LLMProviderResponse


class AIUsageObservabilityTests(SimpleTestCase):
    def test_aggregates_openai_style_usage_across_provider_calls(self):
        responses = [
            LLMProviderResponse(
                provider="openai",
                model="gpt-test",
                text="{}",
                usage={
                    "input_tokens": 100,
                    "output_tokens": 30,
                    "total_tokens": 130,
                    "input_tokens_details": {"cached_tokens": 20},
                },
            ),
            LLMProviderResponse(
                provider="openai",
                model="gpt-test",
                text="{}",
                usage={
                    "prompt_tokens": 40,
                    "completion_tokens": 10,
                    "prompt_tokens_details": {"cached_tokens": 5},
                },
            ),
        ]

        summary = aggregate_provider_usage(responses)

        self.assertEqual(summary.input_tokens, 140)
        self.assertEqual(summary.cached_input_tokens, 25)
        self.assertEqual(summary.output_tokens, 40)
        self.assertEqual(summary.total_tokens, 180)

    @override_settings(
        AI_ASSISTANT_LLM_PRICING_USD_PER_1M_TOKENS={
            "openai": {
                "gpt-test": {
                    "input": "2.00",
                    "cached_input": "0.50",
                    "output": "8.00",
                }
            }
        }
    )
    def test_estimates_cost_from_configured_pricing_without_hardcoding_provider_prices(self):
        cost = estimate_cost_usd(
            provider="openai",
            model="gpt-test",
            input_tokens=1000,
            cached_input_tokens=200,
            output_tokens=300,
        )

        self.assertEqual(cost, Decimal("0.004100"))

    @override_settings(AI_ASSISTANT_LLM_PRICING_USD_PER_1M_TOKENS={})
    def test_returns_none_when_pricing_is_not_configured(self):
        cost = estimate_cost_usd(
            provider="openai",
            model="unknown-model",
            input_tokens=1000,
            cached_input_tokens=0,
            output_tokens=300,
        )

        self.assertIsNone(cost)

    def test_infers_explicit_action_type_before_intent(self):
        request = AssistantTurnRequest(
            user_message=AssistantMessage(role=AssistantMessageRole.USER, content="Hola"),
            metadata={"action_type": "Assistant.Explain_DailyPlan"},
        )
        response = AssistantStructuredResponse(
            assistant_message=AssistantMessage(role=AssistantMessageRole.ASSISTANT, content="Listo"),
            intent=AssistantIntent(name=AssistantIntentName.CREATE_MEAL_PROPOSAL, confidence=0.8),
        )

        self.assertEqual(infer_action_type(request=request, response=response), "assistant.explain_dailyplan")

    def test_infers_meal_proposal_action_type_from_intent(self):
        request = AssistantTurnRequest(
            user_message=AssistantMessage(role=AssistantMessageRole.USER, content="Crea una meal"),
        )
        response = AssistantStructuredResponse(
            assistant_message=AssistantMessage(role=AssistantMessageRole.ASSISTANT, content="Listo"),
            intent=AssistantIntent(name=AssistantIntentName.CREATE_MEAL_PROPOSAL, confidence=0.8),
        )

        self.assertEqual(infer_action_type(request=request, response=response), ACTION_CREATE_MEAL_PROPOSAL)

    def test_defaults_to_chat_action_type(self):
        request = AssistantTurnRequest(
            user_message=AssistantMessage(role=AssistantMessageRole.USER, content="Hola"),
        )
        response = AssistantStructuredResponse(
            assistant_message=AssistantMessage(role=AssistantMessageRole.ASSISTANT, content="Hola"),
        )

        self.assertEqual(infer_action_type(request=request, response=response), ACTION_ASSISTANT_CHAT)

class AIUsageEventStatusChoicesTests(TestCase):
    def test_blocked_status_is_valid_choice_for_guardrail_events(self):
        from ai_assistant.models import AIUsageEvent

        choices = {value for value, _label in AIUsageEvent.Status.choices}

        self.assertIn(AIUsageEvent.Status.BLOCKED, choices)
