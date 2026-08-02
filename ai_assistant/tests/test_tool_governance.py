import json

from django.test import SimpleTestCase, override_settings

from ai_assistant.application import ExternalLLMOrchestrator
from ai_assistant.application.tool_governance import (
    TOOL_SELECTION_REASON_ARGUMENT,
    developer_tool_governance_policy,
    system_tool_restraint_lines,
)
from ai_assistant.application.tools import ReadOnlyToolExecutor, TOOL_READ_PROPOSAL
from ai_assistant.domain import AssistantMessage, AssistantMessageRole, AssistantToolStatus, AssistantTurnRequest
from ai_assistant.infrastructure.providers import LLMProviderResponse, LLMProviderToolCall
from notas.application.ai_tools.results import tool_success


class ScriptedNativeClient:
    provider_name = "openai"
    model = "gpt-test"

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return self.responses.pop(0)


@override_settings(AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=False)
class ToolGovernanceTests(SimpleTestCase):
    def _request(self, content, *, user="user-1"):
        return AssistantTurnRequest(
            user_message=AssistantMessage(role=AssistantMessageRole.USER, content=content),
            context={"surface": "ai_nutrition_intake"},
            metadata={"tool_user": user},
        )

    def test_policy_treats_unresolved_references_as_clarification_not_permission(self):
        system_policy = "\n".join(system_tool_restraint_lines())
        developer_policy = developer_tool_governance_policy()

        self.assertIn("¿qué pasó?", system_policy)
        self.assertIn("no autorizan", system_policy)
        self.assertIn("aclara brevemente", system_policy)
        self.assertEqual(developer_policy["ambiguous"], "clarify_without_tools")
        self.assertFalse(developer_policy["reason_required"])

    def test_provider_request_does_not_pollute_tool_schemas_with_selection_reason(self):
        client = ScriptedNativeClient(
            [
                LLMProviderResponse(
                    provider="openai",
                    model="gpt-test",
                    text=json.dumps(
                        {
                            "format": "ai_assistant_structured_response.v2",
                            "assistant_message": {"content": "¿A qué te refieres exactamente?"},
                            "intent": {
                                "name": "ask_clarification",
                                "confidence": 0.8,
                                "summary": "Referencia ambigua",
                            },
                            "requires_human_review": False,
                        }
                    ),
                )
            ]
        )
        orchestrator = ExternalLLMOrchestrator(llm_client=client)

        orchestrator.continue_turn(self._request("¿Y eso?"))

        provider_request = client.requests[0]
        developer_payload = json.loads(provider_request.messages[1].content)
        self.assertIn("success_criteria", developer_payload)
        for tool in provider_request.tools:
            parameters = tool["parameters"]
            self.assertNotIn(TOOL_SELECTION_REASON_ARGUMENT, parameters["properties"])
            self.assertNotIn(TOOL_SELECTION_REASON_ARGUMENT, parameters["required"])

    def test_native_tool_without_selection_reason_executes_and_remains_observable(self):
        dispatch_calls = []

        def read_proposal(user, *, proposal_id):
            dispatch_calls.append((user, proposal_id))
            return tool_success({"proposal": {"id": proposal_id}})

        client = ScriptedNativeClient(
            [
                LLMProviderResponse(
                    provider="openai",
                    model="gpt-test",
                    text="",
                    response_id="ambiguous-call",
                    tool_calls=(
                        LLMProviderToolCall(
                            name=TOOL_READ_PROPOSAL,
                            arguments={"proposal_id": 12},
                            call_id="ambiguous-read",
                        ),
                    ),
                ),
                LLMProviderResponse(
                    provider="openai",
                    model="gpt-test",
                    text=json.dumps(
                        {
                            "format": "ai_assistant_structured_response.v2",
                            "assistant_message": {"content": "¿Te refieres a la propuesta 12 o a otro elemento?"},
                            "intent": {
                                "name": "ask_clarification",
                                "confidence": 0.9,
                                "summary": "Aclarar el referente",
                            },
                            "requires_human_review": False,
                        }
                    ),
                    response_id="ambiguous-clarification",
                ),
            ]
        )
        response = ExternalLLMOrchestrator(
            llm_client=client,
            read_only_tool_executor=ReadOnlyToolExecutor(
                dispatch_table={TOOL_READ_PROPOSAL: read_proposal}
            ),
        ).continue_turn(self._request("¿Y eso?"))

        self.assertEqual(dispatch_calls, [("user-1", 12)])
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.OK)
        self.assertTrue(response.metadata["tools_executed"])
        self.assertEqual(response.metadata["tool_selection_reasons"][0]["status"], "valid")
        self.assertEqual(
            response.metadata["audit"]["tool_audit"][0]["selection_reason_summary"],
            "explicit read request",
        )

    def test_explicit_selection_reason_executes_and_is_observable_without_arguments(self):
        dispatch_calls = []

        def read_proposal(user, *, proposal_id):
            dispatch_calls.append((user, proposal_id))
            return tool_success({"proposal": {"id": proposal_id, "title": "Plan masa muscular"}})

        selection_reason = "El usuario pidió revisar la propuesta 12."
        client = ScriptedNativeClient(
            [
                LLMProviderResponse(
                    provider="openai",
                    model="gpt-test",
                    text="",
                    response_id="explicit-call",
                    tool_calls=(
                        LLMProviderToolCall(
                            name=TOOL_READ_PROPOSAL,
                            arguments={
                                "proposal_id": 12,
                                TOOL_SELECTION_REASON_ARGUMENT: selection_reason,
                            },
                            call_id="explicit-read",
                        ),
                    ),
                ),
                LLMProviderResponse(
                    provider="openai",
                    model="gpt-test",
                    text=json.dumps(
                        {
                            "format": "ai_assistant_structured_response.v2",
                            "assistant_message": {"content": "La propuesta 12 es Plan masa muscular."},
                            "intent": {
                                "name": "answer_question",
                                "confidence": 0.9,
                                "summary": "Explicar la propuesta solicitada",
                            },
                            "requires_human_review": False,
                        }
                    ),
                    response_id="explicit-answer",
                ),
            ]
        )
        response = ExternalLLMOrchestrator(
            llm_client=client,
            read_only_tool_executor=ReadOnlyToolExecutor(
                dispatch_table={TOOL_READ_PROPOSAL: read_proposal}
            ),
        ).continue_turn(self._request("Revisa la propuesta 12"))

        self.assertEqual(dispatch_calls, [("user-1", 12)])
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.OK)
        self.assertNotIn(TOOL_SELECTION_REASON_ARGUMENT, response.tool_requests[0].arguments)
        observed = response.metadata["tool_selection_reasons"][0]
        self.assertEqual(observed["reason_code"], "explicit_read_request")
        audit_item = response.metadata["audit"]["tool_audit"][0]
        self.assertEqual(audit_item["selection_reason_code"], "explicit_read_request")
        self.assertEqual(audit_item["selection_reason_summary"], "El usuario pidió revisar la propuesta 12.")
        self.assertNotIn("proposal_id", json.dumps(audit_item))
