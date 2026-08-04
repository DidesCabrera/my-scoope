import json

from django.test import SimpleTestCase, override_settings

from ai_assistant.application import AssistantOrchestratorConfig, ExternalLLMOrchestrator
from ai_assistant.application.tools import (
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
    TOOL_READ_DAILYPLAN,
    TOOL_SEARCH_OPERATIONAL_FOODS,
    TOOL_UPDATE_PREFERENCE_DRAFT,
    TOOL_UPDATE_PROFILE_DRAFT,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
    ProfileDraftToolExecutor,
    ReadOnlyToolExecutor,
    ValidationToolExecutor,
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
        self.assertEqual(len(client.requests[1].tool_outputs), 1)
        followup_output = client.requests[1].tool_outputs[0].output
        self.assertEqual(followup_output["status"], "ok")
        self.assertEqual(followup_output["data"]["dailyplan"]["title"], "Plan Base")
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.OK)
        self.assertTrue(response.metadata["tools_executed"])
        self.assertEqual(response.metadata["tool_loop_iterations"], 1)
        self.assertEqual(response.metadata["tool_results_ok"], 1)
        self.assertFalse(response.requires_human_review)
        self.assertTrue(response.metadata["audit"]["tools_executed"])


    def test_executes_validation_tool_and_calls_provider_again_with_results(self):
        calls = []

        def compare_dailyplan(user, *, dailyplan_id, targets, tolerances=None):
            calls.append((user, dailyplan_id, targets, tolerances))
            return tool_success({
                "validation": {
                    "dailyplan_id": dailyplan_id,
                    "summary": "El plan queda bajo el objetivo de proteína.",
                }
            })

        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Voy a comparar tu plan."},
                        "intent": {"name": "answer_question", "confidence": 0.9},
                        "tool_requests": [
                            {
                                "tool_name": TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
                                "arguments": {
                                    "dailyplan_id": 12,
                                    "targets": {"kcal": 2200, "protein": 160},
                                },
                                "request_id": "compare_plan_12",
                            }
                        ],
                        "requires_human_review": False,
                    }
                ),
                json.dumps(
                    {
                        "assistant_message": {"content": "Comparé el plan: falta proteína."},
                        "intent": {"name": "answer_question", "confidence": 0.9},
                        "tool_requests": [],
                        "requires_human_review": False,
                    }
                ),
            ]
        )
        validation_executor = ValidationToolExecutor(
            dispatch_table={TOOL_COMPARE_DAILYPLAN_TO_TARGETS: compare_dailyplan}
        )

        response = ExternalLLMOrchestrator(
            llm_client=client,
            validation_tool_executor=validation_executor,
        ).continue_turn(self._request("Compara mi plan con 2200 kcal"))

        self.assertEqual(response.assistant_text, "Comparé el plan: falta proteína.")
        self.assertEqual(calls, [("user-1", 12, {"kcal": 2200, "protein": 160}, None)])
        self.assertEqual(len(client.requests), 2)
        self.assertEqual(len(client.requests[1].tool_outputs), 1)
        followup_output = client.requests[1].tool_outputs[0].output
        self.assertEqual(followup_output["status"], "ok")
        self.assertEqual(
            followup_output["data"]["validation"]["summary"],
            "El plan queda bajo el objetivo de proteína.",
        )
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.OK)
        self.assertEqual(response.tool_results[0].metadata["executor"], "validation_tool_executor.v1")
        self.assertTrue(response.metadata["tools_executed"])
        self.assertFalse(response.requires_human_review)


    def test_executes_profile_draft_tool_and_calls_provider_again_with_results(self):
        calls = []

        def update_profile_draft(user, *, updates, current_draft=None, field_sources=None):
            calls.append((user, updates, current_draft, field_sources))
            return tool_success({
                "profile_draft": {
                    "height_cm": 188,
                    "field_sources": {"height_cm": "chat_draft"},
                }
            })

        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Voy a actualizar la ficha de esta conversación."},
                        "intent": {"name": "capture_nutrition_brief", "confidence": 0.9},
                        "tool_requests": [
                            {
                                "tool_name": TOOL_UPDATE_PROFILE_DRAFT,
                                "arguments": {"updates": {"height_cm": 188}},
                                "request_id": "profile_draft_1",
                            }
                        ],
                        "requires_human_review": False,
                    }
                ),
                json.dumps(
                    {
                        "assistant_message": {"content": "Perfecto, dejé 188 cm en la ficha de esta conversación."},
                        "intent": {"name": "capture_nutrition_brief", "confidence": 0.9},
                        "tool_requests": [],
                        "requires_human_review": False,
                    }
                ),
            ]
        )
        profile_executor = ProfileDraftToolExecutor(
            dispatch_table={TOOL_UPDATE_PROFILE_DRAFT: update_profile_draft}
        )

        response = ExternalLLMOrchestrator(
            llm_client=client,
            profile_draft_tool_executor=profile_executor,
        ).continue_turn(self._request("Mido 188"))

        self.assertEqual(response.assistant_text, "Perfecto, dejé 188 cm en la ficha de esta conversación.")
        self.assertEqual(calls, [("user-1", {"height_cm": 188}, None, None)])
        self.assertEqual(len(client.requests), 2)
        self.assertEqual(len(client.requests[1].tool_outputs), 1)
        followup_output = client.requests[1].tool_outputs[0].output
        self.assertEqual(followup_output["status"], "ok")
        self.assertEqual(followup_output["data"]["profile_draft"]["height_cm"], 188)
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.OK)
        self.assertEqual(response.tool_results[0].metadata["executor"], "profile_draft_tool_executor.v1")
        self.assertFalse(response.tool_results[0].metadata["writes_allowed"])
        self.assertTrue(response.metadata["tools_executed"])
        self.assertFalse(response.requires_human_review)



    def test_uses_compact_followup_when_full_tool_followup_exceeds_limit(self):
        calls = []

        def update_proposal_preferences(user, *, updates, current_preferences=None, field_sources=None):
            calls.append((user, updates, current_preferences, field_sources))
            return tool_success({
                "proposal_preferences": {
                    "goal": updates.get("goal"),
                    "field_sources": {"goal": "chat_draft"},
                },
                "nutrition_brief_patch": {"goal": updates.get("goal")},
            })

        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Dejo registrado el objetivo."},
                        "intent": {"name": "capture_nutrition_brief", "confidence": 0.9},
                        "tool_requests": [
                            {
                                "tool_name": TOOL_UPDATE_PROPOSAL_PREFERENCES,
                                "arguments": {"updates": {"goal": "muscle_gain"}},
                                "request_id": "proposal_goal_1",
                            }
                        ],
                        "requires_human_review": False,
                    }
                ),
                json.dumps(
                    {
                        "assistant_message": {"content": "Perfecto, lo orientamos a ganar masa muscular."},
                        "intent": {"name": "capture_nutrition_brief", "confidence": 0.9},
                        "tool_requests": [],
                        "requires_human_review": False,
                    }
                ),
            ]
        )
        profile_executor = ProfileDraftToolExecutor(
            dispatch_table={TOOL_UPDATE_PROPOSAL_PREFERENCES: update_proposal_preferences}
        )

        response = ExternalLLMOrchestrator(
            llm_client=client,
            profile_draft_tool_executor=profile_executor,
            config=AssistantOrchestratorConfig(max_input_tokens=2690),
        ).continue_turn(self._request("Quiero aumennter de muscilo"))

        self.assertEqual(response.assistant_text, "Perfecto, lo orientamos a ganar masa muscular.")
        self.assertEqual(calls, [("user-1", {"goal": "muscle_gain"}, None, None)])
        self.assertEqual(len(client.requests), 2)
        self.assertEqual(client.requests[1].metadata["tool_loop"], "controlled_tools.compact_followup.v1")
        self.assertTrue(response.metadata["tools_executed"])
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.OK)
        self.assertNotIn("límite técnico", response.assistant_text.lower())

    def test_executes_preference_draft_tool_and_calls_provider_again_with_results(self):
        calls = []

        def update_preference_draft(user, *, updates, current_draft=None, field_sources=None):
            calls.append((user, updates, current_draft, field_sources))
            return tool_success({
                "preference_draft": {
                    "avoided_foods": updates.get("avoided_foods", []),
                    "preferred_foods": updates.get("preferred_foods", []),
                },
                "preference_draft_card": {
                    "title": "Preferencias para esta propuesta",
                    "sections": [
                        {
                            "title": "Preferencias alimentarias",
                            "items": [
                                {
                                    "key": "avoided_foods",
                                    "label": "Alimentos evitados",
                                    "value": "atun",
                                    "is_pending": False,
                                    "source": "chat_draft",
                                    "source_label": "Este chat",
                                }
                            ],
                        }
                    ],
                    "known_count": 1,
                    "status": "has_data",
                },
            })

        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Voy a ordenar tus preferencias."},
                        "intent": {"name": "capture_nutrition_brief", "confidence": 0.9},
                        "tool_requests": [
                            {
                                "tool_name": TOOL_UPDATE_PREFERENCE_DRAFT,
                                "arguments": {"updates": {"avoided_foods": ["atun"]}},
                                "request_id": "preference_draft_1",
                            }
                        ],
                        "requires_human_review": False,
                    }
                ),
                json.dumps(
                    {
                        "assistant_message": {"content": "Perfecto, dejé registrado que evitas atún para esta propuesta."},
                        "intent": {"name": "capture_nutrition_brief", "confidence": 0.9},
                        "tool_requests": [],
                        "requires_human_review": False,
                    }
                ),
            ]
        )
        profile_executor = ProfileDraftToolExecutor(
            dispatch_table={TOOL_UPDATE_PREFERENCE_DRAFT: update_preference_draft}
        )

        response = ExternalLLMOrchestrator(
            llm_client=client,
            profile_draft_tool_executor=profile_executor,
        ).continue_turn(self._request("Evito el atún"))

        self.assertEqual(response.assistant_text, "Perfecto, dejé registrado que evitas atún para esta propuesta.")
        self.assertEqual(calls, [("user-1", {"avoided_foods": ["atun"]}, None, None)])
        self.assertEqual(len(client.requests), 2)
        self.assertEqual(len(client.requests[1].tool_outputs), 1)
        followup_output = client.requests[1].tool_outputs[0].output
        self.assertEqual(followup_output["status"], "ok")
        self.assertEqual(
            followup_output["data"]["preference_draft"]["avoided_foods"],
            ["atun"],
        )
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.OK)
        self.assertEqual(response.tool_results[0].metadata["executor"], "profile_draft_tool_executor.v1")
        self.assertFalse(response.tool_results[0].metadata["writes_allowed"])
        self.assertTrue(response.metadata["tools_executed"])
        self.assertFalse(response.requires_human_review)

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
                ),
                json.dumps(
                    {
                        "assistant_message": {
                            "content": "No pude leer el plan porque este turno no tiene un usuario autenticado."
                        },
                        "intent": {"name": "read_context", "confidence": 0.8},
                        "tool_requests": [],
                        "requires_human_review": True,
                    }
                ),
            ]
        )

        response = ExternalLLMOrchestrator(llm_client=client).continue_turn(self._request(user=None))

        self.assertEqual(len(client.requests), 2)
        self.assertEqual(len(client.requests[1].tool_outputs), 1)
        self.assertEqual(client.requests[1].tool_outputs[0].output["status"], "blocked")
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
            config=AssistantOrchestratorConfig(max_tool_loop_iterations=1),
        ).continue_turn(self._request())

        self.assertEqual(len(client.requests), 2)
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.OK)
        self.assertEqual(response.tool_results[1].status, AssistantToolStatus.BLOCKED)
        self.assertEqual(response.tool_results[1].error_code, "tool_loop_max_iterations_reached")
        self.assertTrue(response.requires_human_review)
