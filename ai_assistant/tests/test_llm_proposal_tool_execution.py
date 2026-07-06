import json

from django.test import SimpleTestCase, override_settings

from ai_assistant.application import ExternalLLMOrchestrator
from ai_assistant.application.orchestrator import AssistantOrchestratorConfig
from ai_assistant.application.tools import (
    ReviewableProposalToolExecutor,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
)
from ai_assistant.domain import (
    AssistantMessage,
    AssistantMessageRole,
    AssistantToolStatus,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers import FakeLLMClient
from notas.application.ai_tools.results import tool_success


@override_settings(AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=False)
class ExternalLLMReviewableProposalToolExecutionTests(SimpleTestCase):
    def _request(self, content="Crea una propuesta de meal", *, user="user-1"):
        return AssistantTurnRequest(
            user_message=AssistantMessage(role=AssistantMessageRole.USER, content=content),
            context={"surface": "ai_nutrition_intake"},
            metadata={"tool_user": user} if user is not None else {},
        )

    def test_blocks_reviewable_proposal_tool_when_not_enabled(self):
        calls = []

        def create_meal_proposal(user, **kwargs):
            calls.append((user, kwargs))
            return tool_success({"proposal": {"id": 101, "status": "pending_review"}})

        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Crearé una propuesta."},
                        "intent": {"name": "create_meal_proposal", "confidence": 0.9},
                        "tool_requests": [
                            {
                                "tool_name": TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
                                "arguments": {
                                    "dailyplan_id": 12,
                                    "title": "Meal propuesta",
                                    "proposed_payload": {"foods": []},
                                },
                                "request_id": "proposal_1",
                            }
                        ],
                    }
                )
            ]
        )
        executor = ReviewableProposalToolExecutor(
            dispatch_table={TOOL_CREATE_VALIDATED_MEAL_PROPOSAL: create_meal_proposal}
        )

        response = ExternalLLMOrchestrator(
            llm_client=client,
            reviewable_proposal_tool_executor=executor,
        ).continue_turn(self._request())

        self.assertEqual(len(client.requests), 1)
        self.assertEqual(calls, [])
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.BLOCKED)
        self.assertEqual(response.tool_results[0].error_code, "reviewable_proposal_tools_disabled")
        self.assertEqual(response.proposal_ids, ())
        self.assertTrue(response.requires_human_review)

    def test_executes_reviewable_proposal_tool_when_enabled_and_attaches_proposal_id(self):
        calls = []

        def create_meal_proposal(user, *, dailyplan_id, title, proposed_payload, targets=None, summary=""):
            calls.append((user, dailyplan_id, title, proposed_payload, targets, summary))
            return tool_success(
                {
                    "proposal": {
                        "id": 101,
                        "title": title,
                        "status": "pending_review",
                        "proposal_type": "meal",
                    }
                }
            )

        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Crearé una propuesta revisable."},
                        "intent": {"name": "create_meal_proposal", "confidence": 0.9},
                        "tool_requests": [
                            {
                                "tool_name": TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
                                "arguments": {
                                    "dailyplan_id": 12,
                                    "title": "Meal propuesta",
                                    "proposed_payload": {"foods": [{"food_id": 1, "grams": 120}]},
                                    "summary": "Propuesta creada por AI.",
                                },
                                "request_id": "proposal_1",
                            }
                        ],
                    }
                ),
                json.dumps(
                    {
                        "assistant_message": {
                            "content": "Listo, dejé una propuesta revisable para que la apruebes en My Scoope."
                        },
                        "intent": {"name": "create_meal_proposal", "confidence": 0.9},
                        "tool_requests": [],
                        "requires_human_review": True,
                    }
                ),
            ]
        )
        executor = ReviewableProposalToolExecutor(
            dispatch_table={TOOL_CREATE_VALIDATED_MEAL_PROPOSAL: create_meal_proposal}
        )

        response = ExternalLLMOrchestrator(
            llm_client=client,
            reviewable_proposal_tool_executor=executor,
            config=AssistantOrchestratorConfig(enable_reviewable_proposal_tools=True),
        ).continue_turn(self._request())

        self.assertEqual(response.assistant_text, "Listo, dejé una propuesta revisable para que la apruebes en My Scoope.")
        self.assertEqual(calls[0][0], "user-1")
        self.assertEqual(calls[0][1], 12)
        self.assertEqual(len(client.requests), 2)
        followup_payload = "\n".join(message.content for message in client.requests[1].messages)
        self.assertIn("reviewable_proposal_tools_may_create_proposals", followup_payload)
        self.assertIn("101", followup_payload)
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.OK)
        self.assertEqual(response.proposal_ids, (101,))
        self.assertEqual(response.metadata["created_reviewable_proposal_ids"], [101])
        self.assertEqual(response.metadata["proposal_tool_results_ok"], 1)
        self.assertTrue(response.metadata["tools_executed"])
        self.assertTrue(response.requires_human_review)
        self.assertEqual(response.metadata["audit"]["proposal_ids"], [101])
