import json

from django.test import SimpleTestCase, override_settings

from ai_assistant.application.chat_engines import ChatEngineRequest
from ai_assistant.application.context_builder import build_safe_llm_context
from ai_assistant.application.conversational_agency import (
    ASSISTANT_CONVERSATIONAL_AGENCY_VERSION,
    developer_goal_directed_agency_policy,
)
from ai_assistant.application.orchestrator import ExternalLLMOrchestrator
from ai_assistant.application.tools import (
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
)
from ai_assistant.domain import AssistantMessage, AssistantMessageRole, AssistantTurnRequest
from ai_assistant.infrastructure.providers import FakeLLMClient
from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    NutritionConversationState,
    build_llm_intake_result_from_brief,
)


@override_settings(AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=False)
class GoalDirectedAgencyTests(SimpleTestCase):
    def _state(self, brief: NutritionBrief) -> NutritionConversationState:
        return NutritionConversationState(
            messages=[],
            result=build_llm_intake_result_from_brief(brief),
        )

    def test_policy_prefers_progress_without_reintroducing_a_fixed_script(self):
        developer_policy = developer_goal_directed_agency_policy()
        serialized = json.dumps(developer_policy, ensure_ascii=False)

        self.assertEqual(
            developer_policy["version"],
            ASSISTANT_CONVERSATIONAL_AGENCY_VERSION,
        )
        self.assertTrue(developer_policy["active_objective"])
        self.assertTrue(developer_policy["advance_means_progress"])
        self.assertTrue(developer_policy["ready_work_prefers_proposal"])
        self.assertTrue(developer_policy["blocking_info_only"])
        self.assertTrue(developer_policy["no_fixed_flow_or_parser"])
        self.assertNotIn("regex", serialized.lower())
        self.assertNotIn("recommended_tool_sequence", serialized)

    def test_ready_state_is_exposed_as_product_progress_not_question_order(self):
        state = self._state(
            NutritionBrief(
                raw_prompt="Crear propuesta",
                subject_source="self_profile",
                goal="fat_loss",
                requested_entity="daily_plan",
                meals_per_day=3,
                weight_kg=85,
                height_cm=188,
                age_years=38,
                sex="male",
                activity_level="high",
                complexity_level="low",
            )
        )
        request = ChatEngineRequest(message="Con eso basta, avancemos.", user_id=123)

        with self.settings(AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS=True):
            context = build_safe_llm_context(
                request,
                conversation_state=state,
            ).as_dict()

        tool_context = context["metadata"]["tool_oriented_intake"]
        progress = tool_context["work_progress"]
        self.assertEqual(tool_context["version"], "ai_assistant_tool_oriented_intake.v9")
        self.assertEqual(progress["proposal_readiness"], "ready_for_reviewable_proposal")
        self.assertTrue(progress["reviewable_proposal_creation_available"])
        self.assertFalse(progress["required_information_still_missing"])
        self.assertTrue(progress["optional_refinement_is_not_required"])
        self.assertTrue(progress["next_action_is_selected_by_the_assistant"])
        self.assertNotIn("recommended_tool_sequence", str(tool_context))
        self.assertNotIn("visible_follow_up_questions", str(tool_context))

    def test_incomplete_state_exposes_only_blocking_status(self):
        state = self._state(
            NutritionBrief(
                raw_prompt="Quiero un plan",
                subject_source="self_profile",
                goal="muscle_gain",
                requested_entity="daily_plan",
            )
        )
        context = build_safe_llm_context(
            ChatEngineRequest(message="Avancemos", user_id=123),
            conversation_state=state,
        ).as_dict()

        progress = context["metadata"]["tool_oriented_intake"]["work_progress"]
        self.assertEqual(progress["proposal_readiness"], "requires_blocking_information")
        self.assertTrue(progress["required_information_still_missing"])
        self.assertFalse(progress["reviewable_proposal_creation_available"])

    def test_provider_prompt_carries_active_objective_and_advance_policy(self):
        client = FakeLLMClient(
            responses=[
                '{"assistant_message":{"content":"Avancemos."},'
                '"intent":{"name":"create_dailyplan_proposal","confidence":0.9,'
                '"summary":"Crear propuesta"},"requires_human_review":true}'
            ]
        )
        orchestrator = ExternalLLMOrchestrator(llm_client=client)
        request = AssistantTurnRequest(
            user_message=AssistantMessage(
                role=AssistantMessageRole.USER,
                content="Con eso basta, avancemos.",
            )
        )

        orchestrator.continue_turn(request)

        provider_request = client.requests[0]
        developer_payload = json.loads(provider_request.messages[1].content)
        self.assertIn("goal_directed_agency", developer_payload)
        agency = developer_payload["goal_directed_agency"]
        self.assertTrue(agency["active_objective"])
        self.assertTrue(agency["advance_means_progress"])
        self.assertTrue(agency["ready_work_prefers_proposal"])
        self.assertTrue(agency["blocking_info_only"])

    def test_draft_proposal_tool_guides_same_turn_progress_after_advance(self):
        orchestrator = ExternalLLMOrchestrator(llm_client=FakeLLMClient(responses=[]))
        proposal_tool = next(
            spec
            for spec in orchestrator.provider_tool_specs()
            if spec["name"] == TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS
        )

        description = proposal_tool["description"]
        self.assertIn("LLM should prefer it", description)
        self.assertIn("draft tool results are available", description)
        self.assertIn("never applies the proposal directly", description)
