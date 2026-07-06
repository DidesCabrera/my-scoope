import json

from django.test import SimpleTestCase, override_settings

from ai_assistant.application import (
    AssistantOrchestratorConfig,
    ExternalLLMChatEngine,
    ExternalLLMOrchestrator,
)
from ai_assistant.application.chat_engines import ChatEngineRequest
from ai_assistant.application.tools import (
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_READ_DAILYPLAN,
)
from ai_assistant.domain import (
    AssistantIntentName,
    AssistantMessage,
    AssistantMessageRole,
    AssistantToolStatus,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers import FakeLLMClient


@override_settings(AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=False)
class ExternalLLMOrchestratorTests(SimpleTestCase):
    def _request(self, content="Necesito un plan diario de 2200 kcal"):
        return AssistantTurnRequest(
            user_message=AssistantMessage(role=AssistantMessageRole.USER, content=content),
            history=[
                AssistantMessage(role=AssistantMessageRole.USER, content="Hola"),
                AssistantMessage(role=AssistantMessageRole.ASSISTANT, content="Hola, te ayudo."),
            ],
            context={"surface": "ai_nutrition_intake", "secret": "local-only"},
        )

    def test_orchestrator_maps_turn_to_provider_request_with_policy_prompts(self):
        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Puedo ayudarte con eso."},
                        "intent": {"name": "answer_question", "confidence": 0.7},
                        "tool_requests": [],
                        "requires_human_review": False,
                    }
                )
            ]
        )
        orchestrator = ExternalLLMOrchestrator(llm_client=client)

        response = orchestrator.continue_turn(self._request())
        provider_request = client.requests[0]

        self.assertEqual(response.assistant_text, "Puedo ayudarte con eso.")
        self.assertEqual(response.intent.name, AssistantIntentName.ANSWER_QUESTION)
        self.assertFalse(response.requires_human_review)
        self.assertEqual(provider_request.messages[0].role, "system")
        self.assertIn("food_catalog", provider_request.messages[0].content)
        self.assertEqual(provider_request.messages[-1].role, "user")
        provider_payload = "\n".join(message.content for message in provider_request.messages)
        self.assertIn("provider_context", provider_payload)
        self.assertIn("ai_nutrition_intake", provider_payload)
        self.assertNotIn("local-only", provider_payload)
        self.assertNotIn("local-only", json.dumps(provider_request.metadata))
        self.assertEqual(provider_request.metadata["local_context_keys"], ["secret", "surface"])

    def test_orchestrator_blocks_non_read_tools_without_executing_writes(self):
        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "format": "ai_assistant_structured_response.v1",
                        "assistant_message": {"content": "Voy a preparar una solicitud controlada."},
                        "intent": {
                            "name": "create_dailyplan_proposal",
                            "confidence": 0.88,
                            "summary": "Crear propuesta de plan diario",
                        },
                        "tool_requests": [
                            {
                                "tool_name": TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
                                "arguments": {"nutrition_brief": {"target_kcal": 2200}},
                                "request_id": "call_1",
                                "reason": "Crear propuesta revisable desde brief estructurado.",
                            }
                        ],
                        "proposal_ids": [999],
                        "requires_human_review": False,
                    }
                )
            ]
        )

        request = self._request()
        request = AssistantTurnRequest(
            user_message=request.user_message,
            history=request.history,
            context=request.context,
            metadata={"tool_user": "user-1"},
        )

        response = ExternalLLMOrchestrator(llm_client=client).continue_turn(request)

        self.assertEqual(len(response.tool_requests), 1)
        self.assertEqual(len(response.tool_results), 1)
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.BLOCKED)
        self.assertEqual(response.tool_results[0].error_code, "reviewable_proposal_tools_disabled")
        self.assertEqual(response.tool_results[0].tool_name, TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL)
        self.assertTrue(response.requires_human_review)
        self.assertEqual(response.proposal_ids, ())
        self.assertEqual(response.metadata["ignored_provider_proposal_ids"], [999])
        self.assertFalse(response.metadata["tools_executed"])

    def test_orchestrator_blocks_forbidden_or_catalog_tool_requests(self):
        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "No aplicaré cambios directamente."},
                        "intent": {"name": "iterate_proposal", "confidence": 0.9},
                        "tool_requests": [
                            {
                                "tool_name": "apply_proposal",
                                "arguments": {"proposal_id": 1},
                                "request_id": "unsafe_apply",
                            },
                            {
                                "tool_name": TOOL_READ_DAILYPLAN,
                                "arguments": {"dailyplan_id": 10, "catalog_food_id": 99},
                                "request_id": "catalog_leak",
                            },
                        ],
                    }
                )
            ]
        )

        response = ExternalLLMOrchestrator(llm_client=client).continue_turn(self._request("Aplica esta propuesta."))

        self.assertEqual([result.status for result in response.tool_results], [AssistantToolStatus.BLOCKED] * 2)
        self.assertEqual(response.tool_results[0].error_code, "forbidden_ai_assistant_tool")
        self.assertEqual(response.tool_results[1].error_code, "forbidden_catalog_reference")
        self.assertEqual(response.metadata["tool_requests_blocked"], 2)
        self.assertTrue(response.requires_human_review)

    def test_orchestrator_falls_back_safely_for_plain_text_provider_response(self):
        client = FakeLLMClient(responses=["Claro, puedo ayudarte con eso."])

        response = ExternalLLMOrchestrator(llm_client=client).continue_turn(self._request())

        self.assertEqual(response.assistant_text, "Claro, puedo ayudarte con eso.")
        self.assertEqual(response.intent.name, AssistantIntentName.UNKNOWN)
        self.assertTrue(response.requires_human_review)
        self.assertIn("invalid_json", response.metadata["provider_parse_error"])

    def test_orchestrator_falls_back_safely_for_invalid_structured_response(self):
        client = FakeLLMClient(responses=[json.dumps({"assistant_message": {"content": ""}})])

        response = ExternalLLMOrchestrator(llm_client=client).continue_turn(self._request())

        self.assertIn("no cumple el contrato interno", response.assistant_text)
        self.assertEqual(response.intent.name, AssistantIntentName.UNKNOWN)
        self.assertTrue(response.requires_human_review)
        self.assertIn("provider_contract_error", response.metadata)

    def test_orchestrator_bounds_history_sent_to_provider(self):
        client = FakeLLMClient(responses=[json.dumps({"assistant_message": {"content": "Listo."}})])
        orchestrator = ExternalLLMOrchestrator(
            llm_client=client,
            config=AssistantOrchestratorConfig(max_history_messages=1),
        )
        request = AssistantTurnRequest(
            user_message=AssistantMessage(role="user", content="Mensaje actual"),
            history=[
                AssistantMessage(role="user", content="Mensaje antiguo"),
                AssistantMessage(role="assistant", content="Respuesta previa"),
            ],
        )

        orchestrator.continue_turn(request)
        sent_contents = [message.content for message in client.requests[0].messages]

        self.assertIn("Respuesta previa", sent_contents)
        self.assertIn("Mensaje actual", sent_contents)
        self.assertNotIn("Mensaje antiguo", sent_contents)

    def test_external_llm_chat_engine_adapts_chat_engine_contract_without_persistence(self):
        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Respuesta desde motor externo."},
                        "intent": {"name": "answer_question", "confidence": 0.6},
                        "requires_human_review": False,
                    }
                )
            ]
        )
        engine = ExternalLLMChatEngine(orchestrator=ExternalLLMOrchestrator(llm_client=client))

        result = engine.continue_chat(ChatEngineRequest(message="  hola   ", user_id=1))

        self.assertEqual(result.engine_name, "external_llm_chat_engine_v1")
        self.assertEqual(result.assistant_text, "Respuesta desde motor externo.")
        self.assertFalse(result.is_ready_for_proposal)
        self.assertEqual(result.metadata["mode"], "external_llm")
        self.assertFalse(result.metadata["tools_executed"])


    def test_external_llm_chat_engine_sends_safe_context_not_raw_payload(self):
        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Respuesta con contexto seguro."},
                        "intent": {"name": "answer_question", "confidence": 0.6},
                        "requires_human_review": False,
                    }
                )
            ]
        )
        engine = ExternalLLMChatEngine(orchestrator=ExternalLLMOrchestrator(llm_client=client))

        result = engine.continue_chat(
            ChatEngineRequest(
                message="hola",
                user_id=99,
                existing_payload={"api_key": "secret", "raw": "session-value"},
                metadata={"surface": "ai_nutrition_intake"},
            )
        )

        sent_payload = "\n".join(message.content for message in client.requests[0].messages)
        self.assertEqual(result.metadata["context_builder"], "safe_llm_context.v1")
        self.assertIn("provider_context", sent_payload)
        self.assertIn("id_present", sent_payload)
        self.assertIn("existing_payload_present", sent_payload)
        self.assertNotIn("99", sent_payload)
        self.assertNotIn("secret", sent_payload)
        self.assertNotIn("session-value", sent_payload)

    def test_orchestrator_does_not_import_food_catalog_or_operational_models(self):
        import ai_assistant.application.orchestrator as orchestrator

        self.assertNotIn("food_catalog", orchestrator.__dict__)
        self.assertNotIn("notas", orchestrator.__dict__)
        self.assertNotIn("NutritionProposal", orchestrator.__dict__)
