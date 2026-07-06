import json

from django.test import SimpleTestCase, override_settings

from ai_assistant.application import (
    AssistantOrchestratorConfig,
    ExternalLLMOrchestrator,
    resolve_model_route,
    route_max_output_tokens,
)
from ai_assistant.application.model_routing import AIModelRoute, resolve_model_route_for_turn
from ai_assistant.domain import AssistantMessage, AssistantMessageRole, AssistantTurnRequest
from ai_assistant.infrastructure.providers import FakeLLMClient, LLMMessage, LLMProviderRequest, get_llm_client


class NoopUsageRecorder:
    def record_turn(self, **kwargs):
        return {"recorded": False, "test": True}


class AIModelRoutingTests(SimpleTestCase):
    def _turn_request(self, *, action_type="assistant.chat"):
        return AssistantTurnRequest(
            user_message=AssistantMessage(role=AssistantMessageRole.USER, content="Hola"),
            metadata={"action_type": action_type},
        )

    @override_settings(
        AI_ASSISTANT_LLM_PROVIDER="fake",
        AI_ASSISTANT_LLM_MODEL_ROUTES={
            "default": {"provider": "fake", "model": "fake-default", "max_output_tokens": 800},
            "assistant.chat": {"provider": "fake", "model": "fake-mini", "max_output_tokens": 250, "reason": "cheap_chat"},
        },
    )
    def test_resolves_exact_action_route(self):
        route = resolve_model_route("assistant.chat")

        self.assertEqual(route.route_code, "assistant.chat")
        self.assertEqual(route.provider, "fake")
        self.assertEqual(route.model, "fake-mini")
        self.assertEqual(route.max_output_tokens, 250)
        self.assertEqual(route.reason, "cheap_chat")
        self.assertTrue(route.is_specific)

    @override_settings(
        AI_ASSISTANT_LLM_PROVIDER="fake",
        AI_ASSISTANT_LLM_MODEL_ROUTES={
            "default": {"provider": "fake", "model": "fake-default"},
            "assistant.explain.*": {"provider": "fake", "model": "fake-explainer"},
        },
    )
    def test_resolves_prefix_route_before_default(self):
        route = resolve_model_route("assistant.explain_dailyplan")

        self.assertEqual(route.route_code, "assistant.explain.*")
        self.assertEqual(route.model, "fake-explainer")

    @override_settings(
        AI_ASSISTANT_LLM_PROVIDER="fake",
        AI_ASSISTANT_LLM_MODEL_ROUTES={"default": {"provider": "fake", "model": "fake-default"}},
    )
    def test_turn_request_metadata_selects_action_route(self):
        route = resolve_model_route_for_turn(self._turn_request(action_type="Assistant Chat"))

        self.assertEqual(route.action_type, "assistant_chat")
        self.assertEqual(route.model, "fake-default")

    def test_route_max_output_tokens_cannot_exceed_global_guardrail(self):
        route = AIModelRoute(max_output_tokens=1500)

        self.assertEqual(route_max_output_tokens(default_max_output_tokens=900, route=route), 900)
        self.assertEqual(route_max_output_tokens(default_max_output_tokens=900, route=AIModelRoute(max_output_tokens=300)), 300)
        self.assertEqual(route_max_output_tokens(default_max_output_tokens=900, route=AIModelRoute()), 900)

    @override_settings(AI_ASSISTANT_LLM_PROVIDER="fake")
    def test_factory_can_build_fake_client_with_routed_model(self):
        client = get_llm_client(provider_name="fake", model_name="fake-routed")
        response = client.generate(LLMProviderRequest(messages=[LLMMessage(role="user", content="Hola")]))

        self.assertIsInstance(client, FakeLLMClient)
        self.assertEqual(response.model, "fake-routed")

    @override_settings(
        AI_ASSISTANT_LLM_PROVIDER="fake",
        AI_ASSISTANT_LLM_MODEL_ROUTES={
            "default": {"provider": "fake", "model": "fake-default", "max_output_tokens": 900},
            "assistant.ai_nutrition_intake.preview": {
                "provider": "fake",
                "model": "fake-preview-mini",
                "max_output_tokens": 320,
                "reason": "preview_low_cost",
            },
        },
    )
    def test_orchestrator_uses_configured_model_route_when_client_is_not_injected(self):
        orchestrator = ExternalLLMOrchestrator(
            config=AssistantOrchestratorConfig(max_output_tokens=900),
            usage_recorder=NoopUsageRecorder(),
        )
        request = self._turn_request(action_type="assistant.ai_nutrition_intake.preview")

        response = orchestrator.continue_turn(request)

        self.assertEqual(response.metadata["provider_model"], "fake-preview-mini")
        self.assertEqual(response.metadata["usage_observability"]["recorded"], False)
        self.assertEqual(orchestrator.llm_client.requests[0].max_output_tokens, 320)
        self.assertEqual(
            orchestrator.llm_client.requests[0].metadata["model_route"]["route_code"],
            "assistant.ai_nutrition_intake.preview",
        )

    @override_settings(
        AI_ASSISTANT_LLM_PROVIDER="fake",
        AI_ASSISTANT_LLM_MODEL_ROUTES={
            "assistant.chat": {"provider": "fake", "model": "should-not-use"},
        },
    )
    def test_injected_client_still_wins_for_unit_tests_and_custom_callers(self):
        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Listo."},
                        "intent": {"name": "answer_question", "confidence": 0.7},
                    }
                )
            ],
            model="injected-model",
        )
        orchestrator = ExternalLLMOrchestrator(llm_client=client, usage_recorder=NoopUsageRecorder())

        response = orchestrator.continue_turn(self._turn_request(action_type="assistant.chat"))

        self.assertEqual(response.metadata["provider_model"], "injected-model")
        self.assertEqual(client.requests[0].metadata["model_route"]["model"], "should-not-use")
