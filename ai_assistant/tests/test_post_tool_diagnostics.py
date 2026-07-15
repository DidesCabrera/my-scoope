from django.test import SimpleTestCase

from ai_assistant.application import ExternalLLMOrchestrator
from ai_assistant.domain import (
    AssistantMessage,
    AssistantToolResult,
    AssistantToolStatus,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers import (
    FakeLLMClient,
    LLMMessage,
    LLMProviderRequest,
    LLMProviderRequestError,
    LLMProviderToolOutput,
)
from ai_assistant.infrastructure.providers.openai_client import (
    build_openai_responses_payload,
)


class PostToolTransportDiagnosticsTests(SimpleTestCase):
    LIVE_CALL_ID = "call_NdjKFTviYMyNJVQnXNGgvNuv"

    def test_live_provider_call_id_is_preserved_through_tool_result(self):
        request = AssistantTurnRequest(
            user_message=AssistantMessage(role="user", content="Registra cuatro comidas."),
        )
        followup = ExternalLLMOrchestrator(
            llm_client=FakeLLMClient(),
        ).build_tool_followup_provider_request(
            request=request,
            continuation_items=(
                {
                    "type": "function_call",
                    "id": "fc_case_1",
                    "call_id": self.LIVE_CALL_ID,
                    "name": "update_proposal_preferences",
                    "arguments": "{}",
                    "status": "completed",
                },
            ),
            tool_results=(
                AssistantToolResult(
                    tool_name="update_proposal_preferences",
                    status=AssistantToolStatus.OK,
                    request_id=self.LIVE_CALL_ID,
                    data={"proposal_preferences": {"meals_per_day": 4}},
                ),
            ),
            remaining_tool_iterations=0,
        )

        self.assertEqual(followup.tool_outputs[0].call_id, self.LIVE_CALL_ID)
        payload = build_openai_responses_payload(followup, model="gpt-test")
        self.assertEqual(payload["input"][-1]["call_id"], self.LIVE_CALL_ID)

    def test_case_rewritten_output_is_rejected_before_http(self):
        request = LLMProviderRequest(
            messages=[LLMMessage(role="user", content="Usa la herramienta")],
            continuation_items=(
                {
                    "type": "function_call",
                    "id": "fc_case_1",
                    "call_id": self.LIVE_CALL_ID,
                    "name": "update_proposal_preferences",
                    "arguments": "{}",
                    "status": "completed",
                },
            ),
            tool_outputs=(
                LLMProviderToolOutput(
                    call_id=self.LIVE_CALL_ID.lower(),
                    output={"status": "ok"},
                ),
            ),
        )

        with self.assertRaisesMessage(
            LLMProviderRequestError,
            f"missing outputs for ['{self.LIVE_CALL_ID}']",
        ):
            build_openai_responses_payload(request, model="gpt-test")
