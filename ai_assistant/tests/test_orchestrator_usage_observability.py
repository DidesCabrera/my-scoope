import json

from django.test import SimpleTestCase

from ai_assistant.application import ExternalLLMOrchestrator
from ai_assistant.domain import AssistantMessage, AssistantMessageRole, AssistantTurnRequest
from ai_assistant.infrastructure.providers import LLMProviderResponse


class ScriptedUsageClient:
    provider_name = "openai"

    def __init__(self):
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return LLMProviderResponse(
            provider="openai",
            model="gpt-test",
            text=json.dumps(
                {
                    "assistant_message": {"content": "Respuesta medida."},
                    "intent": {"name": "answer_question", "confidence": 0.7},
                    "requires_human_review": False,
                }
            ),
            response_id="resp-usage-1",
            usage={"input_tokens": 120, "output_tokens": 40, "total_tokens": 160},
        )


class CollectingUsageRecorder:
    def __init__(self):
        self.calls = []

    def record_turn(self, **kwargs):
        self.calls.append(kwargs)
        provider_responses = kwargs["provider_responses"]
        return {
            "recorded": True,
            "action_type": "assistant.chat",
            "provider": provider_responses[0].provider,
            "model": provider_responses[0].model,
            "input_tokens": provider_responses[0].usage["input_tokens"],
            "output_tokens": provider_responses[0].usage["output_tokens"],
            "total_tokens": provider_responses[0].usage["total_tokens"],
        }


class ExternalLLMOrchestratorUsageObservabilityTests(SimpleTestCase):
    def test_records_usage_summary_for_successful_turn(self):
        recorder = CollectingUsageRecorder()
        orchestrator = ExternalLLMOrchestrator(
            llm_client=ScriptedUsageClient(),
            usage_recorder=recorder,
        )
        request = AssistantTurnRequest(
            user_message=AssistantMessage(role=AssistantMessageRole.USER, content="Hola"),
            metadata={"action_type": "assistant.chat"},
        )

        response = orchestrator.continue_turn(request)

        self.assertEqual(len(recorder.calls), 1)
        self.assertEqual(recorder.calls[0]["status"], "completed")
        self.assertEqual(response.metadata["usage_observability"]["recorded"], True)
        self.assertEqual(response.metadata["usage_observability"]["input_tokens"], 120)
        self.assertEqual(response.metadata["usage_observability"]["total_tokens"], 160)
