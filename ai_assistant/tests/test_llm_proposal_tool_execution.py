import json

from django.test import SimpleTestCase, override_settings

from ai_assistant.application import ExternalLLMOrchestrator
from ai_assistant.application.orchestrator import AssistantOrchestratorConfig
from ai_assistant.application.tools import (
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
    ReviewableProposalToolExecutor,
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
                ),
                json.dumps(
                    {
                        "assistant_message": {
                            "content": "La creación de propuestas revisables no está habilitada en este entorno."
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
            config=AssistantOrchestratorConfig(enable_reviewable_proposal_tools=False),
        ).continue_turn(self._request())

        self.assertEqual(len(client.requests), 2)
        self.assertEqual(len(client.requests[1].tool_outputs), 1)
        self.assertEqual(client.requests[1].tool_outputs[0].output["status"], "blocked")
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
        self.assertEqual(len(client.requests[1].tool_outputs), 1)
        followup_output = client.requests[1].tool_outputs[0].output
        self.assertEqual(followup_output["status"], "ok")
        self.assertEqual(followup_output["data"]["proposal"]["id"], 101)
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.OK)
        self.assertEqual(response.proposal_ids, (101,))
        self.assertEqual(response.metadata["created_reviewable_proposal_ids"], [101])
        self.assertEqual(response.metadata["proposal_tool_results_ok"], 1)
        self.assertTrue(response.metadata["tools_executed"])
        self.assertTrue(response.requires_human_review)
        self.assertEqual(response.metadata["audit"]["proposal_ids"], [101])

    def test_executes_draft_based_dailyplan_proposal_tool_when_enabled(self):
        calls = []

        def create_dailyplan_from_drafts(user, *, profile_draft, proposal_preferences, preference_draft=None, current_nutrition_brief=None, raw_prompt=""):
            calls.append((user, profile_draft, proposal_preferences, preference_draft, current_nutrition_brief, raw_prompt))
            return tool_success(
                {
                    "proposal": {
                        "id": 202,
                        "title": "DailyPlan desde drafts",
                        "status": "pending_review",
                        "proposal_type": "dailyplan",
                    },
                    "nutrition_brief": {"goal": "muscle_gain", "meals_per_day": 4},
                    "draft_sources": {"profile_draft_used": True, "proposal_preferences_used": True},
                }
            )

        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Crearé la propuesta desde los datos ordenados."},
                        "intent": {"name": "create_dailyplan_proposal", "confidence": 0.9},
                        "tool_requests": [
                            {
                                "tool_name": TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
                                "arguments": {
                                    "profile_draft": {
                                        "weight_kg": 85,
                                        "height_cm": 188,
                                        "age_years": 38,
                                        "sex": "male",
                                        "activity_level": "moderate",
                                    },
                                    "proposal_preferences": {"goal": "muscle_gain", "meals_per_day": 4},
                                    "preference_draft": {"avoided_foods": ["atún"]},
                                },
                                "request_id": "proposal_from_drafts_1",
                            }
                        ],
                    }
                ),
                json.dumps(
                    {
                        "assistant_message": {
                            "content": "Listo, creé una propuesta revisable desde tu ficha y preferencias."
                        },
                        "intent": {"name": "create_dailyplan_proposal", "confidence": 0.9},
                        "tool_requests": [],
                        "requires_human_review": True,
                    }
                ),
            ]
        )
        executor = ReviewableProposalToolExecutor(
            dispatch_table={
                TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS: create_dailyplan_from_drafts
            }
        )

        response = ExternalLLMOrchestrator(
            llm_client=client,
            reviewable_proposal_tool_executor=executor,
            config=AssistantOrchestratorConfig(enable_reviewable_proposal_tools=True),
        ).continue_turn(self._request("Crea la propuesta"))

        self.assertEqual(response.assistant_text, "Listo, creé una propuesta revisable desde tu ficha y preferencias.")
        self.assertEqual(calls[0][0], "user-1")
        self.assertEqual(calls[0][1]["height_cm"], 188)
        self.assertEqual(calls[0][2]["goal"], "muscle_gain")
        self.assertEqual(response.proposal_ids, (202,))
        self.assertEqual(response.metadata["created_reviewable_proposal_ids"], [202])
        self.assertTrue(response.requires_human_review)
        self.assertEqual(len(client.requests[1].tool_outputs), 1)
        followup_output = client.requests[1].tool_outputs[0].output
        self.assertEqual(followup_output["status"], "ok")
        self.assertEqual(followup_output["data"]["proposal"]["id"], 202)
        self.assertTrue(followup_output["data"]["draft_sources"]["profile_draft_used"])
