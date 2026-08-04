import json

from django.test import SimpleTestCase, override_settings

from ai_assistant.application.chat_engines import ChatEngineRequest
from ai_assistant.application.llm_chat_engine import ExternalLLMChatEngine
from ai_assistant.application.orchestrator import (
    AssistantOrchestratorConfig,
    ExternalLLMOrchestrator,
)
from ai_assistant.application.tools import (
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
    TOOL_UPDATE_PROFILE_DRAFT,
    ProfileDraftToolExecutor,
    ReviewableProposalToolExecutor,
)
from ai_assistant.domain import (
    AssistantMessage,
    AssistantMessageRole,
    AssistantStructuredResponse,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers import FakeLLMClient, LLMProviderResponse
from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    required_proposal_fields,
)
from notas.application.ai_tools.results import tool_success
from notas.templatetags.assistant_text import assistant_text


@override_settings(AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=False)
class OutcomeFirstRuntimeTests(SimpleTestCase):
    def test_plain_provider_text_is_a_valid_visible_response(self):
        orchestrator = ExternalLLMOrchestrator(llm_client=FakeLLMClient())

        parsed = orchestrator.parse_provider_response(
            LLMProviderResponse(
                provider="openai",
                model="gpt-test",
                text="Sí. Puedo preparar una propuesta útil con lo que ya me contaste.",
            )
        )

        self.assertEqual(
            parsed.response.assistant_text,
            "Sí. Puedo preparar una propuesta útil con lo que ya me contaste.",
        )
        self.assertEqual(parsed.parse_error, "")
        self.assertFalse(parsed.response.requires_human_review)

    def test_real_chat_history_is_forwarded_with_original_roles(self):
        class CapturingOrchestrator:
            def __init__(self):
                self.request = None

            def continue_turn(self, request):
                self.request = request
                return AssistantStructuredResponse(
                    assistant_message=AssistantMessage(
                        role=AssistantMessageRole.ASSISTANT,
                        content="Continuamos.",
                    )
                )

        orchestrator = CapturingOrchestrator()
        engine = ExternalLLMChatEngine(orchestrator=orchestrator)
        engine.continue_chat(
            ChatEngineRequest(
                message="moderado",
                existing_payload={
                    "messages": [
                        {"role": "user", "text": "Quiero una propuesta para perder grasa."},
                        {"role": "assistant", "text": "¿Cuál es tu nivel de actividad?"},
                    ]
                },
                metadata={"safe_llm_context": {"surface": "ai_nutrition_intake"}},
            )
        )

        self.assertEqual(
            [(message.role.value, message.content) for message in orchestrator.request.history],
            [
                ("user", "Quiero una propuesta para perder grasa."),
                ("assistant", "¿Cuál es tu nivel de actividad?"),
            ],
        )
        self.assertEqual(orchestrator.request.user_message.content, "moderado")

    def test_only_nutritionally_blocking_fields_prevent_a_proposal(self):
        brief = NutritionBrief(
            raw_prompt="Quiero una propuesta",
            goal="fat_loss",
            calorie_target=2200,
        )

        self.assertEqual(required_proposal_fields(brief), [])

    def test_last_blocker_update_forces_proposal_creation_in_same_turn(self):
        proposal_calls = []

        def update_profile(user, *, updates, current_draft=None, sources=None):
            return tool_success(
                {"profile_draft": {**dict(current_draft or {}), **dict(updates or {})}}
            )

        def create_proposal(
            user,
            *,
            profile_draft,
            proposal_preferences,
            preference_draft=None,
            current_nutrition_brief=None,
            raw_prompt="",
        ):
            proposal_calls.append(
                {
                    "user": user,
                    "profile_draft": profile_draft,
                    "proposal_preferences": proposal_preferences,
                    "preference_draft": preference_draft,
                    "current_nutrition_brief": current_nutrition_brief,
                    "raw_prompt": raw_prompt,
                }
            )
            return tool_success(
                {
                    "proposal": {
                        "id": 901,
                        "title": "Propuesta inicial",
                        "status": "pending_review",
                        "proposal_type": "dailyplan",
                    }
                }
            )

        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Registro tu actividad."},
                        "intent": {"name": "capture_nutrition_brief", "confidence": 0.9},
                        "tool_requests": [
                            {
                                "tool_name": TOOL_UPDATE_PROFILE_DRAFT,
                                "arguments": {"updates": {"activity_level": "moderate"}},
                                "request_id": "activity",
                            }
                        ],
                        "requires_human_review": False,
                    }
                ),
                json.dumps(
                    {
                        "assistant_message": {"content": "Ahora creo la propuesta."},
                        "intent": {"name": "create_dailyplan_proposal", "confidence": 0.95},
                        "tool_requests": [
                            {
                                "tool_name": (
                                    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS
                                ),
                                "arguments": {},
                                "request_id": "proposal",
                            }
                        ],
                        "requires_human_review": True,
                    }
                ),
                "Listo. Preparé una propuesta inicial para que la revises.",
            ]
        )
        proposal_executor = ReviewableProposalToolExecutor(
            dispatch_table={
                TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS: create_proposal
            }
        )
        context = {
            "surface": "ai_nutrition_intake",
            "metadata": {
                "tool_oriented_intake": {
                    "current_drafts": {
                        "profile_draft": {
                            "weight_kg": 85,
                            "height_cm": 188,
                            "age_years": 38,
                            "sex": "male",
                        },
                        "preference_draft": {},
                        "proposal_preferences": {"goal": "fat_loss"},
                    },
                    "current_nutrition_brief": {
                        "raw_prompt": "Quiero una propuesta para perder grasa",
                        "goal": "fat_loss",
                        "weight_kg": 85,
                        "height_cm": 188,
                        "age_years": 38,
                        "sex": "male",
                    },
                    "work_progress": {
                        "active_objective": "create_reviewable_dailyplan_proposal",
                        "blocking_fields": ["activity_level"],
                    },
                }
            },
        }

        response = ExternalLLMOrchestrator(
            llm_client=client,
            profile_draft_tool_executor=ProfileDraftToolExecutor(
                dispatch_table={TOOL_UPDATE_PROFILE_DRAFT: update_profile}
            ),
            reviewable_proposal_tool_executor=proposal_executor,
            config=AssistantOrchestratorConfig(
                enable_reviewable_proposal_tools=True,
                max_tool_loop_iterations=4,
            ),
        ).continue_turn(
            AssistantTurnRequest(
                user_message=AssistantMessage(
                    role=AssistantMessageRole.USER,
                    content="moderado",
                ),
                context=context,
                metadata={"tool_user": "user-1"},
            )
        )

        self.assertEqual(response.assistant_text, "Listo. Preparé una propuesta inicial para que la revises.")
        self.assertEqual(response.proposal_ids, (901,))
        self.assertEqual(len(client.requests), 3)
        self.assertEqual(client.requests[1].tool_choice, "required")
        self.assertEqual(
            [tool["name"] for tool in client.requests[1].tools],
            [TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS],
        )
        self.assertEqual(proposal_calls[0]["profile_draft"]["activity_level"], "moderate")
        self.assertEqual(proposal_calls[0]["proposal_preferences"]["goal"], "fat_loss")

    def test_chat_markup_is_readable_and_escapes_untrusted_html(self):
        rendered = str(
            assistant_text(
                "**Propuesta lista**\n- Desayuno simple\n- Cena ligera\n<script>alert(1)</script>"
            )
        )

        self.assertIn("<strong>Propuesta lista</strong>", rendered)
        self.assertIn("<ul><li>Desayuno simple</li><li>Cena ligera</li></ul>", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
