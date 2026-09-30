import json

from django.test import SimpleTestCase, override_settings

from ai_assistant.application import (
    AssistantOrchestratorConfig,
    ExternalLLMChatEngine,
    ExternalLLMOrchestrator,
)
from ai_assistant.application.chat_engines import ChatEngineRequest
from ai_assistant.application.limits import estimate_provider_request_tokens
from ai_assistant.application.model_routing import resolve_model_route_for_turn
from ai_assistant.application.orchestrator import _local_acknowledgement_from_tool_results
from ai_assistant.application.orchestrator_turn import (
    _generate_tool_followup_with_compact_recovery,
)
from ai_assistant.application.product_ports import get_ai_product_bindings
from ai_assistant.application.tool_selection import fact_capture_tool_after_tool_results
from ai_assistant.application.tools import (
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_READ_DAILYPLAN,
    TOOL_READ_PROPOSAL,
    TOOL_READ_USER_PROFILE_CONTEXT,
    TOOL_UPDATE_PROFILE_DRAFT,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
    ProfileDraftToolExecutor,
    ReadOnlyToolExecutor,
)
from ai_assistant.domain import (
    AssistantIntentName,
    AssistantMessage,
    AssistantMessageRole,
    AssistantStructuredResponse,
    AssistantToolResult,
    AssistantToolStatus,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers import (
    FakeLLMClient,
    LLMMessage,
    LLMProviderRequest,
    LLMProviderRequestError,
    LLMProviderResponse,
    LLMProviderToolCall,
)
from notas.application.ai_tools.results import tool_error, tool_success


def _selection_reason(
    summary="El usuario pidió esta operación de forma explícita.",
    **_ignored,
):
    return summary


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
        self.assertIn("resultado útil", provider_request.messages[0].content)
        self.assertIn("Nunca vuelvas a pedir un dato conocido", provider_request.messages[0].content)
        self.assertIn("blocking_fields", provider_request.messages[0].content)
        developer_payload = json.loads(provider_request.messages[1].content)
        self.assertTrue(developer_payload["rules"]["new_facts_require_matching_update_call"])
        self.assertTrue(developer_payload["rules"]["visible_response_is_natural_text"])
        self.assertEqual(provider_request.messages[-1].role, "user")
        provider_payload = "\n".join(message.content for message in provider_request.messages)
        self.assertIn("my_scoope_workspace", provider_payload)
        self.assertIn("ai_nutrition_intake", provider_payload)
        self.assertNotIn("local-only", provider_payload)
        self.assertNotIn("local-only", json.dumps(provider_request.metadata))
        self.assertEqual(provider_request.metadata["local_context_keys"], ["secret", "surface"])
        self.assertEqual(provider_request.metadata["format"], "ai_assistant_natural_response.v1")
        self.assertNotIn("response_json_schema", provider_request.metadata)
        self.assertEqual(provider_request.metadata["reasoning_effort"], "low")
        self.assertEqual(provider_request.tool_choice, "auto")
        self.assertFalse(provider_request.parallel_tool_calls)
        self.assertIn(
            "update_profile_draft",
            {str(spec.get("name") or "") for spec in provider_request.tools},
        )
        self.assertIn("complete_a_ready_active_objective_in_the_same_turn", developer_payload["success_criteria"])

    def test_grouped_facts_require_each_typed_writer_result(self):
        request = AssistantTurnRequest(
            user_message=AssistantMessage(
                role=AssistantMessageRole.USER,
                content=(
                    "Para un futuro plan diario para ganar músculo registra 38 años, "
                    "85 kg, 188 cm, 4 comidas y algo simple."
                ),
            ),
            context={
                "surface": "ai_nutrition_intake",
                "metadata": {
                    "tool_oriented_intake": {
                        "work_progress": {
                            "active_work": {"expected_outcome": "workspace_advanced"}
                        }
                    }
                },
            },
        )
        profile_result = AssistantToolResult(
            tool_name=TOOL_UPDATE_PROFILE_DRAFT,
            status=AssistantToolStatus.OK,
            data={
                "profile_draft": {
                    "age_years": 38,
                    "weight_kg": 85.0,
                    "height_cm": 188,
                }
            },
        )

        next_tool = fact_capture_tool_after_tool_results(
            request,
            (profile_result,),
            enable_reviewable_proposal_tools=True,
            product_bindings=get_ai_product_bindings(),
        )

        self.assertEqual(next_tool, TOOL_UPDATE_PROPOSAL_PREFERENCES)

    def test_ambiguous_reference_is_grounded_even_if_provider_invents_a_plan(self):
        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {
                            "content": "Estoy preparando tu plan diario; todavía faltan datos."
                        },
                        "intent": {"name": "answer_question", "confidence": 0.7},
                        "tool_requests": [],
                        "requires_human_review": False,
                    }
                )
            ]
        )
        request = AssistantTurnRequest(
            user_message=AssistantMessage(
                role=AssistantMessageRole.USER,
                content="¿Qué está pasando?",
            ),
            context={
                "surface": "ai_nutrition_intake",
                "metadata": {
                    "tool_oriented_intake": {
                        "work_progress": {
                            "active_work": {
                                "expected_outcome": "clarification_required",
                                "resource": "none",
                            },
                            "blocking_fields": [],
                        }
                    }
                },
            },
        )

        response = ExternalLLMOrchestrator(llm_client=client).continue_turn(request)

        self.assertIn("No tengo suficiente contexto", response.assistant_text)
        self.assertIn("?", response.assistant_text)
        self.assertNotIn("plan diario", response.assistant_text)
        self.assertTrue(response.metadata["clarification_grounding_guard_applied"])
        self.assertTrue(response.metadata["outcome_trace"]["expected_outcome_met"])

    def test_compound_native_turn_captures_all_facts_under_staging_limit(self):
        class ScriptedNativeClient:
            provider_name = "openai"
            model = "gpt-test"

            def __init__(self):
                self.requests = []
                self.responses = [
                    self._tool_response(
                        TOOL_READ_USER_PROFILE_CONTEXT,
                        {},
                        "read_profile",
                    ),
                    self._tool_response(
                        TOOL_UPDATE_PROFILE_DRAFT,
                        {
                            "updates": {
                                "age_years": 38,
                                "sex": "male",
                                "weight_kg": 85.0,
                                "height_cm": 188,
                                "activity_level": "high",
                                "training_frequency": 3,
                            }
                        },
                        "update_profile",
                    ),
                    self._tool_response(
                        TOOL_UPDATE_PROPOSAL_PREFERENCES,
                        {
                            "updates": {
                                "goal": "muscle_gain",
                                "meals_per_day": 4,
                                "complexity_level": "low",
                            }
                        },
                        "update_preferences",
                    ),
                    LLMProviderResponse(
                        provider="openai",
                        model="gpt-test",
                        text=json.dumps(
                            {
                                "assistant_message": {
                                    "content": "Los datos quedaron listos en esta conversación."
                                },
                                "intent": {"name": "answer_question", "confidence": 0.9},
                                "tool_requests": [],
                                "requires_human_review": False,
                            }
                        ),
                        response_id="final",
                    ),
                ]

            @staticmethod
            def _tool_response(name, arguments, suffix):
                arguments = {
                    **arguments,
                    "reason": "El usuario pidió registrar explícitamente estos datos.",
                }
                return LLMProviderResponse(
                    provider="openai",
                    model="gpt-test",
                    text="",
                    response_id=f"response_{suffix}",
                    tool_calls=(
                        LLMProviderToolCall(
                            name=name,
                            arguments=arguments,
                            call_id=f"call_{suffix}",
                        ),
                    ),
                    continuation_items=(
                        {
                            "type": "function_call",
                            "id": f"fc_{suffix}",
                            "call_id": f"call_{suffix}",
                            "name": name,
                            "arguments": json.dumps(arguments),
                            "status": "completed",
                        },
                    ),
                )

            def generate(self, request):
                self.requests.append(request)
                return self.responses.pop(0)

        def read_profile(user):
            return tool_success({"profile_context": {"source": "persisted_profile"}})

        def update_profile(user, *, updates, current_draft=None, field_sources=None):
            return tool_success({"profile_draft": dict(updates)})

        def update_preferences(user, *, updates, current_preferences=None, field_sources=None):
            return tool_success({"proposal_preferences": dict(updates)})

        client = ScriptedNativeClient()
        orchestrator = ExternalLLMOrchestrator(
            llm_client=client,
            read_only_tool_executor=ReadOnlyToolExecutor(
                dispatch_table={TOOL_READ_USER_PROFILE_CONTEXT: read_profile}
            ),
            profile_draft_tool_executor=ProfileDraftToolExecutor(
                dispatch_table={
                    TOOL_UPDATE_PROFILE_DRAFT: update_profile,
                    TOOL_UPDATE_PROPOSAL_PREFERENCES: update_preferences,
                }
            ),
            config=AssistantOrchestratorConfig(
                max_input_tokens=6000,
                max_context_chars=8000,
                max_tool_loop_iterations=6,
            ),
        )
        message = (
            "Para un futuro plan diario orientado a ganar músculo, usa mi ficha "
            "personal como base y registra en esta conversación: 38 años, hombre, "
            "85 kg, 188 cm, fuerza 3 veces por semana con actividad alta, 4 comidas "
            "y algo simple. Por ahora solo deja los datos listos."
        )
        request = AssistantTurnRequest(
            user_message=AssistantMessage(role=AssistantMessageRole.USER, content=message),
            context={
                "surface": "ai_nutrition_intake",
                "metadata": {
                    "tool_oriented_intake": {
                        "current_drafts": {},
                        "work_progress": {
                            "active_work": {
                                "expected_outcome": "workspace_advanced",
                                "resource": "profile",
                            },
                            "blocking_fields": [],
                        },
                    }
                },
            },
            metadata={"tool_user": "user-1"},
        )

        response = orchestrator.continue_turn(request)

        self.assertEqual(
            [result.tool_name for result in response.tool_results],
            [
                TOOL_READ_USER_PROFILE_CONTEXT,
                TOOL_UPDATE_PROFILE_DRAFT,
                TOOL_UPDATE_PROPOSAL_PREFERENCES,
            ],
        )
        self.assertEqual(len(client.requests), 4)
        self.assertEqual(
            client.requests[1].tool_choice,
            {"type": "function", "name": TOOL_UPDATE_PROFILE_DRAFT},
        )
        self.assertEqual(
            client.requests[2].tool_choice,
            {"type": "function", "name": TOOL_UPDATE_PROPOSAL_PREFERENCES},
        )
        self.assertTrue(
            all(
                estimate_provider_request_tokens(provider_request) <= 6000
                for provider_request in client.requests
            )
        )
        self.assertEqual(
            response.assistant_text,
            "Los datos quedaron listos en esta conversación.",
        )

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

        response = ExternalLLMOrchestrator(
            llm_client=client,
            config=AssistantOrchestratorConfig(enable_reviewable_proposal_tools=False),
        ).continue_turn(request)

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
        self.assertEqual(response.intent.name, AssistantIntentName.ANSWER_QUESTION)
        self.assertFalse(response.requires_human_review)
        self.assertNotIn("provider_parse_error", response.metadata)

    def test_orchestrator_falls_back_safely_for_invalid_structured_response(self):
        client = FakeLLMClient(responses=[json.dumps({"assistant_message": {"content": ""}})])

        response = ExternalLLMOrchestrator(llm_client=client).continue_turn(self._request())

        self.assertIn("no cumple el contrato interno", response.assistant_text)
        self.assertEqual(response.intent.name, AssistantIntentName.UNKNOWN)
        self.assertTrue(response.requires_human_review)
        self.assertIn("provider_contract_error", response.metadata)

    @override_settings(
        AI_ASSISTANT_LLM_MODEL_ROUTES={
            "default": {
                "provider": "fake",
                "model": "fake-llm",
                "max_output_tokens": 900,
            }
        }
    )
    def test_cm24_validation_uses_explicit_diagnostic_output_budget(self):
        orchestrator = ExternalLLMOrchestrator(
            llm_client=FakeLLMClient(),
            config=AssistantOrchestratorConfig(max_output_tokens=1400),
        )
        request = self._request("Valida un turno estructurado.")
        request = AssistantTurnRequest(
            user_message=request.user_message,
            history=request.history,
            context=request.context,
            metadata={"cm24_validation": True},
        )

        provider_request = orchestrator.build_provider_request(request)

        self.assertEqual(provider_request.max_output_tokens, 1400)


    def test_provider_request_hides_disabled_reviewable_proposal_tools(self):
        orchestrator = ExternalLLMOrchestrator(
            llm_client=FakeLLMClient(),
            config=AssistantOrchestratorConfig(enable_reviewable_proposal_tools=False),
        )

        provider_request = orchestrator.build_provider_request(self._request("Ayúdame con una propuesta."))
        tool_names = {str(tool.get("name") or "") for tool in provider_request.tools}

        self.assertIn("update_proposal_preferences", tool_names)
        self.assertNotIn("create_validated_meal_proposal", tool_names)
        self.assertNotIn("create_nutrition_engine_dailyplan_proposal_from_drafts", tool_names)
        developer_payload = json.loads(provider_request.messages[1].content)
        self.assertTrue(developer_payload["rules"]["new_facts_require_matching_update_call"])

    def test_provider_request_keeps_generic_proposal_surface_compact(self):
        orchestrator = ExternalLLMOrchestrator(
            llm_client=FakeLLMClient(),
            config=AssistantOrchestratorConfig(enable_reviewable_proposal_tools=True),
        )

        provider_request = orchestrator.build_provider_request(self._request("Prepara una propuesta revisable."))
        tool_names = {str(tool.get("name") or "") for tool in provider_request.tools}

        self.assertIn("create_nutrition_engine_dailyplan_proposal_from_drafts", tool_names)
        self.assertNotIn("query_workspace", tool_names)
        self.assertNotIn("list_user_programs", tool_names)
        self.assertNotIn("read_calendarization", tool_names)
        self.assertNotIn("propose_workspace_patch", tool_names)
        self.assertNotIn("read_account_billing_context", tool_names)

    def test_structured_plan_request_fits_staging_guardrail_with_exact_first_tool(self):
        orchestrator = ExternalLLMOrchestrator(
            llm_client=FakeLLMClient(),
            config=AssistantOrchestratorConfig(
                max_input_tokens=6000,
                max_context_chars=8000,
                max_output_tokens=900,
            ),
        )
        context = {
            "surface": "ai_nutrition_intake",
            "conversation": {"message_count": 0},
            "metadata": {
                "tool_oriented_intake": {
                    "current_drafts": {},
                    "current_nutrition_brief": {"bounded_noise": "x" * 7000},
                    "work_progress": {
                        "active_objective": "create_reviewable_dailyplan_proposal",
                        "active_work": {
                            "expected_outcome": "nutrition_proposal",
                            "resource": "dailyplan",
                        },
                        "blocking_fields": ["weight_kg"],
                    },
                }
            },
        }
        request = AssistantTurnRequest(
            user_message=AssistantMessage(
                role=AssistantMessageRole.USER,
                content=(
                    "Crea ahora un plan diario de 2400 kcal con 30% proteína, "
                    "50% carbohidratos y 20% grasas para un hombre de 38 años, "
                    "80 kg, 180 cm, actividad alta, fuerza 4 veces por semana y 4 comidas."
                ),
            ),
            context=context,
        )

        provider_request = orchestrator.build_provider_request(request)

        self.assertLessEqual(estimate_provider_request_tokens(provider_request), 6000)
        self.assertEqual(
            provider_request.tool_choice,
            {"type": "function", "name": "update_profile_draft"},
        )
        self.assertEqual(
            {tool["name"] for tool in provider_request.tools},
            {
                "update_profile_draft",
                "update_proposal_preferences",
                "create_nutrition_engine_dailyplan_proposal_from_drafts",
            },
        )

    def test_intake_exposes_profile_and_preference_reads_when_user_invokes_memory(self):
        orchestrator = ExternalLLMOrchestrator(
            llm_client=FakeLLMClient(),
            config=AssistantOrchestratorConfig(enable_reviewable_proposal_tools=True),
        )

        provider_request = orchestrator.build_provider_request(
            self._request("Usa mi ficha y mis preferencias guardadas para crear el plan.")
        )
        tool_names = {str(tool.get("name") or "") for tool in provider_request.tools}

        self.assertIn("read_user_profile_context", tool_names)
        self.assertNotIn("share_profile_draft_card", tool_names)
        self.assertIn("read_user_preference_context", tool_names)
        self.assertNotIn("share_preference_draft_card", tool_names)

    def test_intake_exposes_cards_only_when_user_requests_presentation(self):
        orchestrator = ExternalLLMOrchestrator(
            llm_client=FakeLLMClient(),
            config=AssistantOrchestratorConfig(enable_reviewable_proposal_tools=True),
        )

        provider_request = orchestrator.build_provider_request(
            self._request("Muéstrame mi ficha y mis preferencias guardadas.")
        )
        tool_names = {str(tool.get("name") or "") for tool in provider_request.tools}

        self.assertIn("read_user_profile_context", tool_names)
        self.assertIn("share_profile_draft_card", tool_names)
        self.assertIn("read_user_preference_context", tool_names)
        self.assertIn("share_preference_draft_card", tool_names)

    def test_parser_accepts_v2_json_string_slots_and_tool_arguments(self):
        orchestrator = ExternalLLMOrchestrator(llm_client=FakeLLMClient())
        parse_result = orchestrator.parse_provider_response(
            LLMProviderResponse(
                provider="openai",
                model="gpt-test",
                text=json.dumps(
                    {
                        "format": "ai_assistant_structured_response.v2",
                        "assistant_message": {"content": "Voy a registrar ese cambio."},
                        "intent": {
                            "name": "capture_nutrition_brief",
                            "confidence": 0.9,
                            "summary": "Cambiar objetivo",
                            "slots_json": json.dumps({"goal": "fat_loss"}),
                            "missing_slots": [],
                            "safety_flags": [],
                        },
                        "tool_plan": {
                            "required": True,
                            "summary": "Actualizar preferencias de propuesta",
                        },
                        "tool_requests": [
                            {
                                "tool_name": "update_proposal_preferences",
                                "arguments_json": json.dumps({"goal": "fat_loss"}),
                                "request_id": "change-goal",
                                "reason": "El usuario corrigió su objetivo.",
                            }
                        ],
                        "requires_human_review": False,
                    }
                ),
            )
        )

        self.assertFalse(parse_result.parse_error)
        self.assertTrue(parse_result.declared_tools_required)
        self.assertEqual(parse_result.response.intent.slots["goal"], "fat_loss")
        self.assertEqual(parse_result.response.tool_requests[0].arguments["goal"], "fat_loss")

    def test_openai_contract_repair_retries_initial_operational_intent_without_tools(self):
        class ScriptedOpenAIClient:
            provider_name = "openai"
            model = "gpt-test"

            def __init__(self):
                self.requests = []
                self.responses = [
                    LLMProviderResponse(
                        provider="openai",
                        model="gpt-test",
                        text=json.dumps(
                            {
                                "format": "ai_assistant_structured_response.v2",
                                "assistant_message": {"content": "Entendido, será un plan para ganar músculo."},
                                "intent": {
                                    "name": "capture_nutrition_brief",
                                    "confidence": 0.9,
                                    "summary": "Capturar dirección inicial",
                                    "slots_json": "{}",
                                    "missing_slots": [],
                                    "safety_flags": [],
                                },
                                "tool_plan": {
                                    "required": False,
                                    "summary": "No tools",
                                },
                                "tool_requests": [],
                                "requires_human_review": False,
                            }
                        ),
                        response_id="ungrounded-1",
                    ),
                    LLMProviderResponse(
                        provider="openai",
                        model="gpt-test",
                        text=json.dumps(
                            {
                                "format": "ai_assistant_structured_response.v2",
                                "assistant_message": {"content": "Registraré esa dirección."},
                                "intent": {
                                    "name": "capture_nutrition_brief",
                                    "confidence": 0.9,
                                    "summary": "Capturar dirección inicial",
                                    "slots_json": json.dumps({
                                        "goal": "muscle_gain",
                                        "requested_entity": "daily_plan",
                                    }),
                                    "missing_slots": [],
                                    "safety_flags": [],
                                },
                                "tool_plan": {
                                    "required": True,
                                    "summary": "Actualizar dirección de propuesta",
                                },
                                "tool_requests": [
                                    {
                                        "tool_name": "update_proposal_preferences",
                                        "arguments_json": json.dumps(
                                            {
                                                "updates": {
                                                    "goal": "muscle_gain",
                                                    "requested_entity": "daily_plan",
                                                }
                                            }
                                        ),
                                        "request_id": "proposal-direction-1",
                                        "reason": "Registrar la dirección solicitada.",
                                    }
                                ],
                                "requires_human_review": False,
                            }
                        ),
                        response_id="grounded-2",
                    ),
                    LLMProviderResponse(
                        provider="openai",
                        model="gpt-test",
                        text=json.dumps(
                            {
                                "format": "ai_assistant_structured_response.v2",
                                "assistant_message": {"content": "No pude registrar el cambio sin un usuario autenticado."},
                                "intent": {
                                    "name": "capture_nutrition_brief",
                                    "confidence": 0.7,
                                    "summary": "Resultado de tool no aplicado",
                                },
                                "requires_human_review": True,
                            }
                        ),
                        response_id="followup-3",
                    ),
                ]

            def generate(self, request):
                self.requests.append(request)
                return self.responses.pop(0)

        client = ScriptedOpenAIClient()
        response = ExternalLLMOrchestrator(llm_client=client).continue_turn(
            self._request("Quiero un plan diario para ganar masa muscular.")
        )

        self.assertEqual(len(client.requests), 3)
        self.assertEqual(client.requests[1].tool_choice, "required")
        self.assertTrue(response.metadata["provider_contract_repair_attempted"])
        self.assertEqual(response.tool_requests[0].tool_name, "update_proposal_preferences")

    def test_openai_contract_repair_retries_malformed_or_ungrounded_envelope_once(self):
        class ScriptedOpenAIClient:
            provider_name = "openai"
            model = "gpt-test"

            def __init__(self):
                self.requests = []
                self.responses = [
                    LLMProviderResponse(
                        provider="openai",
                        model="gpt-test",
                        text="{",
                        response_id="bad-1",
                        raw={
                            "status": "incomplete",
                            "incomplete_details": {"reason": "max_output_tokens"},
                        },
                    ),
                    LLMProviderResponse(
                        provider="openai",
                        model="gpt-test",
                        text=json.dumps(
                            {
                                "format": "ai_assistant_structured_response.v2",
                                "assistant_message": {"content": "Necesito registrar el objetivo."},
                                "intent": {
                                    "name": "capture_nutrition_brief",
                                    "confidence": 0.9,
                                    "summary": "Objetivo de ganancia muscular",
                                    "slots_json": json.dumps({"goal": "muscle_gain"}),
                                    "missing_slots": [],
                                    "safety_flags": [],
                                },
                                "tool_plan": {
                                    "required": True,
                                    "summary": "Actualizar la propuesta",
                                },
                                "tool_requests": [
                                    {
                                        "tool_name": "update_proposal_preferences",
                                        "arguments_json": json.dumps({"goal": "muscle_gain"}),
                                        "request_id": "goal-1",
                                        "reason": "Registrar el objetivo entregado.",
                                    }
                                ],
                                "requires_human_review": False,
                            }
                        ),
                        response_id="repaired-2",
                    ),
                    LLMProviderResponse(
                        provider="openai",
                        model="gpt-test",
                        text=json.dumps(
                            {
                                "format": "ai_assistant_structured_response.v2",
                                "assistant_message": {"content": "No pude registrar el cambio sin un usuario autenticado."},
                                "intent": {
                                    "name": "capture_nutrition_brief",
                                    "confidence": 0.7,
                                    "summary": "Resultado de tool no aplicado",
                                },
                                "requires_human_review": True,
                            }
                        ),
                        response_id="followup-3",
                    ),
                ]

            def generate(self, request):
                self.requests.append(request)
                return self.responses.pop(0)

        client = ScriptedOpenAIClient()
        orchestrator = ExternalLLMOrchestrator(llm_client=client)

        response = orchestrator.continue_turn(self._request("Quiero ganar masa muscular."))

        self.assertEqual(len(client.requests), 3)
        self.assertEqual(client.requests[1].metadata["contract_repair"], "incomplete_response_retry.v1")
        self.assertTrue(response.metadata["provider_contract_repair_attempted"])
        self.assertEqual(response.metadata["provider_incomplete_reasons"], ["max_output_tokens"])
        self.assertEqual(response.metadata["provider_final_incomplete_reason"], "")
        self.assertEqual(response.tool_requests[0].tool_name, "update_proposal_preferences")

    def test_parser_maps_provider_native_function_calls_without_text_envelope(self):
        orchestrator = ExternalLLMOrchestrator(llm_client=FakeLLMClient())

        parse_result = orchestrator.parse_provider_response(
            LLMProviderResponse(
                provider="openai",
                model="gpt-test",
                text="",
                tool_calls=(
                    LLMProviderToolCall(
                        name="update_proposal_preferences",
                        arguments={
                            "updates": {
                                "goal": "fat_loss",
                                "requested_entity": "program",
                            },
                            "reason": _selection_reason(
                                reason_code="new_or_corrected_user_facts",
                                reference_resolution="new_facts_in_current_message",
                                summary="El usuario indicó el objetivo y el tipo de propuesta.",
                            ),
                        },
                        call_id="call_native_1",
                    ),
                ),
            )
        )

        self.assertFalse(parse_result.parse_error)
        self.assertEqual(parse_result.response.tool_requests[0].request_id, "call_native_1")
        self.assertEqual(
            parse_result.response.tool_requests[0].arguments["updates"]["goal"],
            "fat_loss",
        )
        self.assertNotIn("reason", parse_result.response.tool_requests[0].arguments)
        self.assertEqual(
            parse_result.response.tool_requests[0].metadata["selection_reason_code"],
            "new_or_corrected_user_facts",
        )
        self.assertTrue(parse_result.response.metadata["provider_native_tool_transport"])

    def test_native_strict_proposal_call_drops_nullable_fields_not_stated(self):
        orchestrator = ExternalLLMOrchestrator(llm_client=FakeLLMClient())

        parse_result = orchestrator.parse_provider_response(
            LLMProviderResponse(
                provider="openai",
                model="gpt-test",
                text="",
                tool_calls=(
                    LLMProviderToolCall(
                        name="update_proposal_preferences",
                        arguments={
                            "updates": {
                                "goal": "muscle_gain",
                                "requested_entity": "daily_plan",
                                "meals_per_day": 4,
                                "complexity_level": "low",
                                "energy_adjustment": None,
                                "calorie_target": None,
                                "protein_target": None,
                                "carb_target": None,
                                "fat_target": None,
                                "notes": None,
                            },
                            "reason": _selection_reason(
                                reason_code="new_or_corrected_user_facts",
                                reference_resolution="new_facts_in_current_message",
                                summary="El usuario entregó preferencias para la propuesta.",
                            ),
                        },
                        call_id="call_strict_preferences",
                    ),
                ),
            )
        )

        updates = parse_result.response.tool_requests[0].arguments["updates"]
        self.assertEqual(
            updates,
            {
                "goal": "muscle_gain",
                "requested_entity": "daily_plan",
                "meals_per_day": 4,
                "complexity_level": "low",
            },
        )


    def test_provider_call_id_keeps_exact_case_through_tool_result_transport(self):
        orchestrator = ExternalLLMOrchestrator(llm_client=FakeLLMClient())
        request = self._request("Registra cuatro comidas.")
        followup = orchestrator.build_tool_followup_provider_request(
            request=request,
            continuation_items=(
                {
                    "type": "function_call",
                    "id": "fc_case_1",
                    "call_id": "call_NdjKFTviYMyNJVQnXNGgvNuv",
                    "name": "update_proposal_preferences",
                    "arguments": "{}",
                    "status": "completed",
                },
            ),
            tool_results=(
                AssistantToolResult(
                    tool_name="update_proposal_preferences",
                    status=AssistantToolStatus.OK,
                    request_id="call_NdjKFTviYMyNJVQnXNGgvNuv",
                    data={"proposal_preferences": {"meals_per_day": 4}},
                ),
            ),
            remaining_tool_iterations=0,
        )

        self.assertEqual(
            followup.tool_outputs[0].call_id,
            "call_NdjKFTviYMyNJVQnXNGgvNuv",
        )

    def test_native_function_call_results_are_returned_as_function_call_outputs(self):
        class ScriptedNativeClient:
            provider_name = "openai"
            model = "gpt-test"

            def __init__(self):
                self.requests = []
                self.responses = [
                    LLMProviderResponse(
                        provider="openai",
                        model="gpt-test",
                        text="",
                        response_id="native-call-1",
                        tool_calls=(
                            LLMProviderToolCall(
                                name="read_proposal",
                                arguments={
                                    "proposal_id": 2147483647,
                                    "reason": _selection_reason(
                                        summary="El usuario pidió revisar la propuesta 2147483647.",
                                    ),
                                },
                                call_id="call_read_1",
                            ),
                        ),
                        continuation_items=(
                            {
                                "type": "function_call",
                                "id": "fc_1",
                                "call_id": "call_read_1",
                                "name": "read_proposal",
                                "arguments": '{"proposal_id":2147483647}',
                                "status": "completed",
                            },
                        ),
                    ),
                    LLMProviderResponse(
                        provider="openai",
                        model="gpt-test",
                        text=json.dumps(
                            {
                                "format": "ai_assistant_structured_response.v2",
                                "assistant_message": {"content": "No encontré esa propuesta."},
                                "intent": {
                                    "name": "read_context",
                                    "confidence": 0.9,
                                    "summary": "Proposal not found",
                                },
                                "requires_human_review": False,
                            }
                        ),
                        response_id="native-final-2",
                    ),
                ]

            def generate(self, request):
                self.requests.append(request)
                return self.responses.pop(0)

        client = ScriptedNativeClient()
        response = ExternalLLMOrchestrator(llm_client=client).continue_turn(
            self._request("Revisa la propuesta 2147483647.")
        )

        self.assertEqual(len(client.requests), 2)
        followup = client.requests[1]
        self.assertEqual(followup.metadata["tool_loop"], "native_function_calls.v1")
        self.assertEqual(followup.tool_outputs[0].call_id, "call_read_1")
        self.assertEqual(followup.tool_outputs[0].output["status"], "blocked")
        self.assertEqual(followup.continuation_items[0]["type"], "function_call")
        self.assertEqual(response.assistant_text, "No encontré esa propuesta.")
        self.assertEqual(response.tool_requests[0].tool_name, "read_proposal")
        self.assertTrue(response.metadata["provider_native_tool_transport"])

    def test_post_tool_local_ack_reports_state_without_selecting_next_question(self):
        result = AssistantToolResult(
            tool_name=TOOL_UPDATE_PROPOSAL_PREFERENCES,
            status=AssistantToolStatus.OK,
            data={
                "proposal_preferences": {
                    "goal": "fat_loss",
                    "requested_entity": "program",
                    "meals_per_day": 3,
                }
            },
        )

        acknowledgement = _local_acknowledgement_from_tool_results((result,))

        self.assertEqual(
            acknowledgement,
            "La dirección de la propuesta quedó actualizada.",
        )
        self.assertNotIn("Para seguir", acknowledgement)
        self.assertNotIn("?", acknowledgement)

    def test_native_tool_result_survives_provider_followup_failure(self):
        class FailingFollowupClient:
            provider_name = "openai"
            model = "gpt-test"

            def __init__(self):
                self.requests = []

            def generate(self, request):
                self.requests.append(request)
                if len(self.requests) == 1:
                    return LLMProviderResponse(
                        provider="openai",
                        model="gpt-test",
                        text="",
                        response_id="native-read-1",
                        tool_calls=(
                            LLMProviderToolCall(
                                name=TOOL_READ_PROPOSAL,
                                arguments={
                                    "proposal_id": 2147483647,
                                    "reason": _selection_reason(
                                        summary="El usuario pidió revisar la propuesta 2147483647.",
                                    ),
                                },
                                call_id="call_read_missing",
                            ),
                        ),
                        continuation_items=(
                            {
                                "type": "function_call",
                                "id": "fc_missing",
                                "call_id": "call_read_missing",
                                "name": TOOL_READ_PROPOSAL,
                                "arguments": '{"proposal_id":2147483647}',
                                "status": "completed",
                            },
                        ),
                        usage={"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
                    )
                raise LLMProviderRequestError("follow-up rejected")

        def read_missing_proposal(user, *, proposal_id):
            return tool_error(
                code="not_found",
                message="The requested resource was not found or is not available for this user.",
            )

        client = FailingFollowupClient()
        orchestrator = ExternalLLMOrchestrator(
            llm_client=client,
            read_only_tool_executor=ReadOnlyToolExecutor(
                dispatch_table={TOOL_READ_PROPOSAL: read_missing_proposal}
            ),
        )
        request = AssistantTurnRequest(
            user_message=AssistantMessage(
                role=AssistantMessageRole.USER,
                content="Revisa la propuesta 2147483647.",
            ),
            context={"surface": "ai_nutrition_intake"},
            metadata={"tool_user": "user-1", "debug_ai_assistant": True},
        )

        response = orchestrator.continue_turn(request)

        self.assertEqual(len(client.requests), 2)
        self.assertIn("No encontré una propuesta disponible", response.assistant_text)
        self.assertEqual(response.tool_results[0].status, AssistantToolStatus.ERROR)
        self.assertEqual(response.tool_results[0].error_code, "not_found")
        self.assertTrue(response.metadata["provider_native_tool_transport"])
        self.assertEqual(response.metadata["provider_native_tool_calls"], 1)
        self.assertTrue(response.metadata["tool_followup_local_ack"])
        self.assertEqual(
            response.metadata["tool_followup_local_ack_policy"],
            "state_ack_only.v2",
        )
        self.assertTrue(response.metadata["provider_tool_followup_failed"])
        self.assertTrue(response.metadata["post_tool_degraded"])
        self.assertEqual(
            response.metadata["post_tool_degradation_reason"],
            "provider_followup_failed",
        )
        self.assertEqual(
            response.metadata["provider_tool_followup_error_type"],
            "LLMProviderRequestError",
        )
        self.assertEqual(response.metadata["debug_status"], "degraded")
        self.assertEqual(
            response.metadata["debug_error_type"],
            "tool_followup_LLMProviderRequestError",
        )

    def test_native_final_followup_recovers_once_with_compact_request(self):
        class RecoveringFollowupClient:
            provider_name = "openai"
            model = "gpt-test"

            def __init__(self):
                self.requests = []

            def generate(self, request):
                self.requests.append(request)
                if len(self.requests) == 1:
                    return LLMProviderResponse(
                        provider="openai",
                        model="gpt-test",
                        text="",
                        response_id="native-update-1",
                        tool_calls=(
                            LLMProviderToolCall(
                                name=TOOL_UPDATE_PROPOSAL_PREFERENCES,
                                arguments={
                                    "updates": {"goal": "fat_loss"},
                                    "reason": _selection_reason(
                                        summary="El usuario pidió orientar la propuesta a bajar grasa.",
                                    ),
                                },
                                call_id="call_update_goal",
                            ),
                        ),
                        continuation_items=(
                            {
                                "type": "function_call",
                                "id": "fc_update_goal",
                                "call_id": "call_update_goal",
                                "name": TOOL_UPDATE_PROPOSAL_PREFERENCES,
                                "arguments": '{"updates":{"goal":"fat_loss"}}',
                                "status": "completed",
                            },
                        ),
                    )
                if len(self.requests) == 2:
                    raise LLMProviderRequestError("native continuation rejected")
                return LLMProviderResponse(
                    provider="openai",
                    model="gpt-test",
                    text=json.dumps(
                        {
                            "assistant_message": {
                                "content": "Listo, orienté la propuesta a bajar grasa."
                            },
                            "intent": {
                                "name": "capture_nutrition_brief",
                                "confidence": 0.9,
                            },
                            "tool_requests": [
                                {
                                    "tool_name": TOOL_UPDATE_PROPOSAL_PREFERENCES,
                                    "arguments": {"updates": {"goal": "muscle_gain"}},
                                    "request_id": "must_not_execute",
                                }
                            ],
                        }
                    ),
                    response_id="compact-final-1",
                )

        captured_updates = []

        def update_proposal_preferences(
            user,
            *,
            updates,
            current_preferences=None,
            field_sources=None,
        ):
            captured_updates.append(dict(updates))
            return tool_success(
                {
                    "proposal_preferences": {
                        "goal": updates["goal"],
                        "field_sources": {"goal": "chat_draft"},
                    },
                    "nutrition_brief_patch": {"goal": updates["goal"]},
                }
            )

        client = RecoveringFollowupClient()
        orchestrator = ExternalLLMOrchestrator(
            llm_client=client,
            profile_draft_tool_executor=ProfileDraftToolExecutor(
                dispatch_table={
                    TOOL_UPDATE_PROPOSAL_PREFERENCES: update_proposal_preferences
                }
            ),
        )
        request = AssistantTurnRequest(
            user_message=AssistantMessage(
                role=AssistantMessageRole.USER,
                content="Quiero bajar grasa.",
            ),
            context={
                "surface": "ai_nutrition_intake",
                "metadata": {
                    "tool_oriented_intake": {
                        "work_progress": {
                            "active_work": {
                                "expected_outcome": "workspace_advanced",
                            }
                        }
                    }
                },
            },
            metadata={"tool_user": "user-1", "debug_ai_assistant": True},
        )

        response = orchestrator.continue_turn(request)

        self.assertEqual(len(client.requests), 3)
        self.assertEqual(
            client.requests[2].metadata["tool_loop"],
            "controlled_tools.compact_followup.v1",
        )
        self.assertEqual(
            response.assistant_text,
            "Listo, orienté la propuesta a bajar grasa.",
        )
        self.assertTrue(response.metadata["provider_tool_followup_compact_recovery"])
        self.assertEqual(response.metadata["provider_tool_followup_compact_recovery_count"], 1)
        self.assertEqual(response.metadata["tool_free_followup_tool_requests_ignored"], 1)
        self.assertEqual(captured_updates, [{"goal": "fat_loss"}])
        self.assertEqual(
            [item.request_id for item in response.tool_requests],
            ["call_update_goal"],
        )
        self.assertFalse(response.metadata.get("provider_tool_followup_failed", False))
        self.assertEqual(response.metadata["debug_status"], "completed")

    def test_completed_proposal_recovers_even_when_followup_still_offers_tools(self):
        class RecoveringClient:
            provider_name = "openai"
            model = "gpt-test"

            def __init__(self):
                self.requests = []

            def generate(self, request):
                self.requests.append(request)
                if len(self.requests) == 1:
                    raise LLMProviderRequestError("native continuation rejected")
                return LLMProviderResponse(
                    provider="openai",
                    model="gpt-test",
                    text="La propuesta quedó creada y lista para revisión.",
                )

        client = RecoveringClient()
        orchestrator = ExternalLLMOrchestrator(llm_client=client)
        request = self._request("Crea una comida de 450 kcal.")
        provider_request = LLMProviderRequest(
            messages=(LLMMessage(role="user", content=request.user_message.content),),
            metadata={"tool_loop": "native_function_calls.v1"},
            tools=(
                {
                    "name": TOOL_UPDATE_PROPOSAL_PREFERENCES,
                    "parameters": {"type": "object", "properties": {}},
                },
            ),
        )
        proposal_result = AssistantToolResult(
            tool_name="create_nutrition_solver_meal_proposal",
            status=AssistantToolStatus.OK,
            data={"proposal_id": 73},
        )
        first_response = AssistantStructuredResponse(
            assistant_message=AssistantMessage(
                role=AssistantMessageRole.ASSISTANT,
                content="Estoy creando la propuesta.",
            )
        )

        recovered_request, recovered_response, error, recovery_count = (
            _generate_tool_followup_with_compact_recovery(
                orchestrator,
                turn_llm_client=client,
                request=request,
                provider_request=provider_request,
                first_response=first_response,
                tool_results=(proposal_result,),
                model_route=resolve_model_route_for_turn(request),
            )
        )

        self.assertIsNone(error)
        self.assertIsNotNone(recovered_response)
        self.assertEqual(recovery_count, 1)
        self.assertEqual(len(client.requests), 2)
        self.assertEqual(tuple(recovered_request.tools), ())
        self.assertEqual(
            recovered_request.metadata["tool_loop"],
            "controlled_tools.compact_followup.v1",
        )

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
        self.assertIn("my_scoope_workspace", sent_payload)
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
