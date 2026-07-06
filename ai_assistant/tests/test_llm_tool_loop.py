import json

from django.test import SimpleTestCase, override_settings

from ai_assistant.application import ExternalLLMOrchestrator
from ai_assistant.application.tools import ReadOnlyToolExecutor, TOOL_READ_DAILYPLAN, TOOL_SEARCH_OPERATIONAL_FOODS
from ai_assistant.domain import (
    AssistantMessage,
    AssistantMessageRole,
    AssistantToolStatus,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers import FakeLLMClient
from notas.application.ai_tools.results import tool_success


@override_settings(AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=False)
class ExternalLLMToolLoopTests(SimpleTestCase):
    def _request(self, content="Lee mi plan 12", *, user="user-1"):
        return AssistantTurnRequest(
            user_message=AssistantMessage(role=AssistantMessageRole.USER, content=content),
            context={"surface": "ai_nutrition_intake"},
            metadata={"tool_user": user} if user is not None else {},
        )

    def test_executes_read_only_tool_and_calls_provider_again_with_results(self):
        calls = []

        def read_dailyplan(user, *, dailyplan_id):
            calls.append((user, dailyplan_id))
            return tool_success({"dailyplan": {"id": dailyplan_id, "title": "Plan Base"}})

        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Voy a leer tu plan."},
                        "intent": {"name": "read_context", "confidence": 0.9},
                        "tool_requests": [
                            {
                                "tool_name": TOOL_READ_DAILYPLAN,
                                "arguments": {"dailyplan_id": 12},
                                "request_id": "read_plan_12",
                            }
                        ],
                        "requires_human_review": False,
                    }
                ),
                json.dumps(
                    {
                        "assistant_message": {"content": "Tu plan se llama Plan Base."},
                        "intent": {"name": "answer_question", "confidence": 0.9},
                        "tool_requests": [],
                        "requires_human_review": False,
                    }
                ),
            ]
        )
        executor = ReadOnlyToolExecutor(dispatch_table={TOOL_READ_DAILYPLAN: read_dailyplan})

        response = ExternalLLMOrchestrator(
            llm_client=client,
            read_only_tool_executor=executor,
        ).continue_turn(self._request())

        self.assertEqual(response.assistant_text, "Tu plan se llama Plan Base.")
        self.assertEqual(calls, [("user-1", 12)])
        self.assertEqual(len(client.requests), 2)
        followup_payload = "\n".join(message.content for message in client.requests[1].messages)
        self.assertIn("tool_results", followup_payload)
        self.assertIn("Plan Base", followup_payload)
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.OK)
        self.assertTrue(response.metadata["tools_executed"])
        self.assertEqual(response.metadata["tool_loop_iterations"], 1)
        self.assertEqual(response.metadata["tool_results_ok"], 1)
        self.assertFalse(response.requires_human_review)
        self.assertTrue(response.metadata["audit"]["tools_executed"])

    def test_blocks_read_only_tool_loop_without_authenticated_tool_user(self):
        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Intentaré leer tu plan."},
                        "intent": {"name": "read_context", "confidence": 0.8},
                        "tool_requests": [
                            {
                                "tool_name": TOOL_READ_DAILYPLAN,
                                "arguments": {"dailyplan_id": 12},
                                "request_id": "read_plan_12",
                            }
                        ],
                    }
                )
            ]
        )

        response = ExternalLLMOrchestrator(llm_client=client).continue_turn(self._request(user=None))

        self.assertEqual(len(client.requests), 1)
        self.assertFalse(response.metadata["tools_executed"])
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.BLOCKED)
        self.assertEqual(response.tool_results[0].error_code, "tool_user_required")
        self.assertTrue(response.requires_human_review)

    def test_blocks_additional_tool_requests_from_second_provider_call(self):
        def search_foods(user, *, query, limit):
            return tool_success({"foods": [{"id": 1, "name": "Arroz"}]})

        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Buscaré alimentos."},
                        "intent": {"name": "read_context", "confidence": 0.8},
                        "tool_requests": [
                            {
                                "tool_name": TOOL_SEARCH_OPERATIONAL_FOODS,
                                "arguments": {"query": "arroz", "limit": 5},
                                "request_id": "search_1",
                            }
                        ],
                    }
                ),
                json.dumps(
                    {
                        "assistant_message": {"content": "Encontré arroz."},
                        "intent": {"name": "answer_question", "confidence": 0.8},
                        "tool_requests": [
                            {
                                "tool_name": TOOL_SEARCH_OPERATIONAL_FOODS,
                                "arguments": {"query": "pollo"},
                                "request_id": "search_2",
                            }
                        ],
                    }
                ),
            ]
        )
        executor = ReadOnlyToolExecutor(dispatch_table={TOOL_SEARCH_OPERATIONAL_FOODS: search_foods})

        response = ExternalLLMOrchestrator(
            llm_client=client,
            read_only_tool_executor=executor,
        ).continue_turn(self._request())

        self.assertEqual(len(client.requests), 2)
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.OK)
        self.assertEqual(response.tool_results[1].status, AssistantToolStatus.BLOCKED)
        self.assertEqual(response.tool_results[1].error_code, "tool_loop_max_iterations_reached")
        self.assertTrue(response.requires_human_review)
