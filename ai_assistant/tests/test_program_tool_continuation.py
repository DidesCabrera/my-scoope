import json
from dataclasses import replace
from unittest.mock import Mock

from django.test import SimpleTestCase

from ai_assistant.application.limits import estimate_provider_request_tokens
from ai_assistant.application.orchestrator import AssistantOrchestratorConfig, ExternalLLMOrchestrator
from ai_assistant.application.tools import (
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS as CREATE,
)
from ai_assistant.application.tools import (
    TOOL_UPDATE_PROPOSAL_PREFERENCES as UPDATE,
)
from ai_assistant.domain import (
    AssistantMessage,
    AssistantStructuredResponse,
    AssistantToolRequest,
    AssistantToolResult,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers import FakeLLMClient


class ProgramToolContinuationTests(SimpleTestCase):
    def setUp(self):
        self.orchestrator = ExternalLLMOrchestrator(
            llm_client=FakeLLMClient(),
            config=AssistantOrchestratorConfig(enable_reviewable_proposal_tools=True, max_input_tokens=6000),
        )
        self.request = AssistantTurnRequest(
            user_message=AssistantMessage(role="user", content=(
                "Crea un programa de 8 semanas, 2400 kcal diarias. Indica cuántos menús distintos tiene."
            )),
            context={"surface": "ai_nutrition_intake", "metadata": {"tool_oriented_intake": {
                "work_progress": {"active_objective": "create_reviewable_program_proposal", "blocking_fields": ["goal"],
                    "active_work": {"resource": "program", "expected_outcome": "nutrition_proposal"}},
            }}},
        )
        self.captured = AssistantToolResult(tool_name=UPDATE, status="ok", request_id="capture", data={
            "proposal_preferences": {"requested_entity": "program", "duration_weeks": 8,
                "calorie_target": 2400, "meals_per_day": 4,
                "macro_distribution": {"protein": 30, "carbs": 50, "fat": 20}},
        })

    def followup(self, results, *, remaining=3, continuation=()):
        return self.orchestrator.build_tool_followup_provider_request(
            request=self.request, continuation_items=continuation, tool_results=results[-1:],
            accumulated_tool_results=results, remaining_tool_iterations=remaining,
        )

    def test_menu_count_request_does_not_replace_creation_with_library_query(self):
        initial = self.orchestrator.build_provider_request(self.request)
        self.assertNotIn("query_workspace", {tool["name"] for tool in initial.tools})
        self.assertEqual(initial.tool_choice, {"type": "function", "name": UPDATE})

    def test_large_history_keeps_pending_program_creation_and_complete_draft(self):
        followup = self.followup((self.captured,), continuation=({"type": "message", "content": "history " * 8000},))
        self.assertEqual(followup.tool_choice, {"type": "function", "name": CREATE})
        self.assertEqual([tool["name"] for tool in followup.tools], [CREATE])
        self.assertLessEqual(estimate_provider_request_tokens(followup), 6000)
        self.assertEqual(followup.continuation_items, ())
        self.assertEqual(followup.tool_outputs, ())
        self.assertEqual(json.loads(followup.messages[-1].content)["latest_typed_drafts"]["proposal_preferences"],
                         self.captured.data["proposal_preferences"])
        self.assertIn(self.request.user_message.content, [m.content for m in followup.messages])

    def test_successful_program_is_not_created_again(self):
        created = AssistantToolResult(tool_name=CREATE, status="ok", request_id="created",
                                      data={"proposal": {"id": 123, "status": "pending_review"}})
        followup = self.followup((self.captured, created))
        self.assertEqual(followup.tools, ())
        self.assertIsNone(followup.tool_choice)

    def test_compaction_does_not_extend_exhausted_iteration_budget(self):
        followup = self.followup((self.captured,), remaining=0)
        self.assertEqual(followup.tools, ())
        self.assertIsNone(followup.tool_choice)

    def weekly_request(self):
        return replace(self.request, user_message=AssistantMessage(role="user", content=
            "Crea un programa de ocho semanas con peso proyectado de 85 a 80 kg y proteína entre 2 y 2.2 g/kg."))

    def test_weekly_constraints_in_notes_keep_typed_capture_pending(self):
        self.request = self.weekly_request()
        # Only the terminal weight has an explicit kg suffix in this fixture.
        profile = AssistantToolResult(tool_name="update_profile_draft", status="ok", data={"profile_draft": {"weight_kg": 80.0}})
        result = self.followup((profile, self.captured))
        self.assertEqual(result.tool_choice, {"type": "function", "name": UPDATE})
        self.assertTrue(any("program_specification completo" in message.content for message in result.messages))

    def test_large_history_keeps_pending_weekly_capture_executable(self):
        self.request = self.weekly_request()
        profile = AssistantToolResult(tool_name="update_profile_draft", status="ok", data={"profile_draft": {"weight_kg": 80.0}})
        result = self.followup((profile,), continuation=({"type": "message", "content": "history " * 8000},))
        self.assertEqual(result.tool_choice, {"type": "function", "name": UPDATE})
        self.assertEqual([tool["name"] for tool in result.tools], [UPDATE])
        self.assertEqual(result.continuation_items, ())
        self.assertLessEqual(estimate_provider_request_tokens(result), 6000)
        self.assertEqual(json.loads(result.messages[-1].content)["latest_typed_drafts"]["profile_draft"], {"weight_kg": 80.0})

    def test_weekly_creation_cannot_fall_back_to_legacy_scalar_path(self):
        self.request = self.weekly_request()
        self.orchestrator._execute_validated_tool_request = Mock()
        result = self.orchestrator._resolve_tool_results(self.request, (AssistantToolRequest(tool_name=CREATE),),
                                                       prior_tool_results=(self.captured,))[0]
        self.assertEqual(result.error_code, "weekly_program_specification_required")
        self.orchestrator._execute_validated_tool_request.assert_not_called()

    def test_weekly_typed_spec_unlocks_creation(self):
        from nutrition_solver.tests.test_program_specification import example_spec
        self.request = self.weekly_request()
        profile = AssistantToolResult(tool_name="update_profile_draft", status="ok", data={"profile_draft": {"weight_kg": 80.0}})
        captured = replace(self.captured, data={"proposal_preferences": {"program_specification": example_spec()}})
        self.assertEqual(self.followup((profile, captured)).tool_choice, {"type": "function", "name": CREATE})

    def test_false_weekly_completion_is_not_shown_as_success(self):
        from ai_assistant.application.orchestrator_turn import _enforce_program_completion
        response = AssistantStructuredResponse(assistant_message=AssistantMessage(role="assistant", content="He preparado tu programa revisable."))
        guarded = _enforce_program_completion(response, request=self.weekly_request(), tool_results=(self.captured,))
        self.assertIn("todavía no he creado", guarded.assistant_text)
        created = replace(response, proposal_ids=(123,))
        self.assertIs(_enforce_program_completion(created, request=self.weekly_request(), tool_results=()), created)

    def test_explicit_projected_reference_blocks_wrong_capture_then_allows_correction(self):
        from nutrition_solver.tests.test_program_specification import example_spec
        self.request = replace(self.weekly_request(), user_message=AssistantMessage(role="user", content=(
            "Crea una propuesta de programa de 8 semanas. Peso medido 85 kg. "
            "Usa explícitamente peso proyectado lineal desde 85 hasta 80 kg como referencia de proteína, "
            "no como medición ni garantía. Proteína entre 2 y 2.2 g/kg."
        )))
        profile = AssistantToolResult(tool_name="update_profile_draft", status="ok", data={"profile_draft": {"weight_kg": 85}})
        spec = example_spec()
        wrong = replace(self.captured, data={"proposal_preferences": {"program_specification": {**spec, "weight_basis": "measured"}}})
        followup = self.followup((profile, wrong))
        self.assertEqual(followup.tool_choice, {"type": "function", "name": UPDATE})
        self.assertTrue(any("weight_basis='projected'" in message.content for message in followup.messages))
        self.orchestrator._execute_validated_tool_request = Mock()
        blocked = self.orchestrator._resolve_tool_results(self.request, (AssistantToolRequest(tool_name=CREATE),),
                                                        prior_tool_results=(profile, wrong))[0]
        self.assertEqual(blocked.error_code, "weekly_program_specification_required")
        self.orchestrator._execute_validated_tool_request.assert_not_called()
        corrected = replace(wrong, data={"proposal_preferences": {"program_specification": {**spec, "weight_basis": "projected"}}})
        self.assertEqual(self.followup((profile, wrong, corrected)).tool_choice, {"type": "function", "name": CREATE})

    def test_explicit_reference_guard_applies_to_saved_draft(self):
        from ai_assistant.application.program_capture import weekly_specification_missing
        request = replace(self.weekly_request(), user_message=AssistantMessage(role="user", content=
            "Crea un programa. Usa peso proyectado para calcular la proteína."))
        request.context["metadata"]["tool_oriented_intake"]["current_drafts"] = {
            "proposal_preferences": {"program_specification": {"weight_basis": "measured"}},
        }
        self.assertTrue(weekly_specification_missing(request, ()))

    def test_weight_reference_detection_does_not_infer_from_baseline_or_negation(self):
        from ai_assistant.application.program_capture import explicit_protein_weight_basis
        cases = (
            ("Peso medido 85 kg y peso proyectado 80 kg, proteína 2 g/kg.", None),
            ("No uses peso proyectado para calcular la proteína.", None),
            ("No debes usar peso proyectado para calcular la proteína.", None),
            ("¿Debo usar peso proyectado como referencia de proteína?", None),
            ("Si uso peso proyectado para calcular la proteína, ¿qué cambia?", None),
            ("Usa peso medido como referencia de proteína. Peso proyectado 80 kg.", "measured"),
            ("Utiliza el peso actual para calcular la proteína.", "measured"),
            ("Usa peso proyectado lineal de 85.5 a 80.5 kg como referencia de proteína.", "projected"),
            ("Usa peso proyectado para proteína. Usa peso medido para proteína.", None),
        )
        for text, expected in cases:
            with self.subTest(text=text):
                request = replace(self.request, user_message=AssistantMessage(role="user", content=text))
                self.assertEqual(explicit_protein_weight_basis(request), expected)
