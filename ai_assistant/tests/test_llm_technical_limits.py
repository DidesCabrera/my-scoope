import json

from django.test import SimpleTestCase, override_settings

from ai_assistant.application import AssistantOrchestratorConfig, ExternalLLMOrchestrator
from ai_assistant.application.limits import estimate_text_tokens
from ai_assistant.application.tools import TOOL_READ_DAILYPLAN
from ai_assistant.domain import AssistantMessage, AssistantMessageRole, AssistantTurnRequest
from ai_assistant.infrastructure.providers import FakeLLMClient


class SummaryUsageRecorder:
    def record_turn(self, **kwargs):
        return {"recorded": False, "status": kwargs.get("status"), "error_type": kwargs.get("error_type", "")}


class ExternalLLMTechnicalLimitsTests(SimpleTestCase):
    def _request(self, *, content="Hola", history=(), context=None):
        return AssistantTurnRequest(
            user_message=AssistantMessage(role=AssistantMessageRole.USER, content=content),
            history=tuple(history or ()),
            context=dict(context or {}),
            metadata={"action_type": "assistant.chat"},
        )

    def test_blocks_provider_call_when_estimated_input_tokens_exceed_limit(self):
        client = FakeLLMClient(responses=[json.dumps({"assistant_message": {"content": "No debería llamarse."}})])
        orchestrator = ExternalLLMOrchestrator(
            llm_client=client,
            config=AssistantOrchestratorConfig(max_input_tokens=10),
            usage_recorder=SummaryUsageRecorder(),
        )

        response = orchestrator.continue_turn(self._request(content="palabra " * 200))

        self.assertEqual(client.requests, [])
        self.assertTrue(response.metadata["technical_limit_blocked"])
        self.assertEqual(response.metadata["technical_limit_error_code"], "ai_input_token_limit_exceeded")
        self.assertEqual(response.metadata["usage_observability"].get("status"), "blocked")
        self.assertTrue(response.requires_human_review)

    def test_truncates_history_messages_before_sending_to_provider(self):
        client = FakeLLMClient(responses=[json.dumps({"assistant_message": {"content": "Listo."}})])
        orchestrator = ExternalLLMOrchestrator(
            llm_client=client,
            config=AssistantOrchestratorConfig(max_message_chars=256),
            usage_recorder=SummaryUsageRecorder(),
        )
        long_history = "historial " * 40

        orchestrator.continue_turn(
            self._request(
                content="Mensaje actual",
                history=[AssistantMessage(role=AssistantMessageRole.USER, content=long_history)],
            )
        )

        sent_history = [message for message in client.requests[0].messages if message.role == "user"][0]
        self.assertLessEqual(len(sent_history.content), 256)
        self.assertTrue(sent_history.content.endswith("…"))

    def test_blocks_tool_requests_above_per_turn_limit(self):
        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Revisaré varias tools."},
                        "intent": {"name": "read_context", "confidence": 0.8},
                        "tool_requests": [
                            {"tool_name": TOOL_READ_DAILYPLAN, "arguments": {"dailyplan_id": 1}, "request_id": "tool_1"},
                            {"tool_name": TOOL_READ_DAILYPLAN, "arguments": {"dailyplan_id": 2}, "request_id": "tool_2"},
                            {"tool_name": TOOL_READ_DAILYPLAN, "arguments": {"dailyplan_id": 3}, "request_id": "tool_3"},
                        ],
                    }
                )
            ]
        )
        orchestrator = ExternalLLMOrchestrator(
            llm_client=client,
            config=AssistantOrchestratorConfig(max_tool_requests_per_turn=1),
            usage_recorder=SummaryUsageRecorder(),
        )

        response = orchestrator.continue_turn(self._request(content="Lee varios planes"))

        self.assertEqual(len(response.tool_results), 3)
        self.assertEqual(response.tool_results[0].error_code, "tool_user_required")
        self.assertEqual(response.tool_results[1].error_code, "tool_requests_per_turn_limit_exceeded")
        self.assertEqual(response.tool_results[2].error_code, "tool_requests_per_turn_limit_exceeded")
        self.assertEqual(response.metadata["tool_requests_blocked"], 3)
        self.assertTrue(response.requires_human_review)

    @override_settings(
        AI_ASSISTANT_MAX_HISTORY_MESSAGES=2,
        AI_ASSISTANT_MAX_OUTPUT_TOKENS=333,
        AI_ASSISTANT_MAX_TOOL_LOOP_ITERATIONS=0,
        AI_ASSISTANT_MAX_INPUT_TOKENS=444,
        AI_ASSISTANT_MAX_CONTEXT_CHARS=555,
        AI_ASSISTANT_MAX_MESSAGE_CHARS=666,
        AI_ASSISTANT_MAX_TOOL_REQUESTS_PER_TURN=7,
        AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS=True,
    )
    def test_config_can_be_loaded_from_django_settings(self):
        config = AssistantOrchestratorConfig.from_settings()

        self.assertEqual(config.max_history_messages, 2)
        self.assertEqual(config.max_output_tokens, 333)
        self.assertEqual(config.max_tool_loop_iterations, 0)
        self.assertEqual(config.max_input_tokens, 444)
        self.assertEqual(config.max_context_chars, 555)
        self.assertEqual(config.max_message_chars, 666)
        self.assertEqual(config.max_tool_requests_per_turn, 7)
        self.assertTrue(config.enable_reviewable_proposal_tools)

    def test_token_estimator_is_stable_without_provider_specific_tokenizer(self):
        self.assertEqual(estimate_text_tokens(""), 0)
        self.assertEqual(estimate_text_tokens("abcd"), 1)
        self.assertEqual(estimate_text_tokens("abcde"), 2)
