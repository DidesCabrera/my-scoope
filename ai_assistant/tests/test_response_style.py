import json

from django.test import SimpleTestCase

from notas.application.ai_intake import deterministic_policy
from ai_assistant.application.orchestrator import ExternalLLMOrchestrator
from ai_assistant.application.response_style import (
    ASSISTANT_RESPONSE_STYLE_VERSION,
    developer_response_style_policy,
    format_numbered_questions,
)
from ai_assistant.application.tools import (
    TOOL_UPDATE_PROFILE_DRAFT,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
)
from ai_assistant.infrastructure.providers import FakeLLMClient


class AssistantResponseStylePolicyTests(SimpleTestCase):
    def setUp(self):
        self.orchestrator = ExternalLLMOrchestrator(llm_client=FakeLLMClient(responses=[]))

    def test_system_prompt_uses_adaptive_pacing_without_fixed_intake_order(self):
        system_prompt = self.orchestrator._system_prompt()

        self.assertIn("los campos ausentes no forman por sí solos un cuestionario", system_prompt)
        self.assertIn("Puedes responder, confirmar, preguntar o solicitar tools", system_prompt)
        self.assertNotIn("acompaña al usuario por etapas", system_prompt)
        self.assertNotIn("pregunta solo el siguiente bloque útil", system_prompt)
        self.assertNotIn("solo una pregunta visible por turno", system_prompt)
        self.assertNotIn("preguntas obligatorias", system_prompt)

    def test_developer_response_policy_allows_zero_one_or_grouped_questions(self):
        policy = developer_response_style_policy()
        serialized = json.dumps(policy, ensure_ascii=False)

        self.assertEqual(policy["version"], ASSISTANT_RESPONSE_STYLE_VERSION)
        self.assertEqual(ASSISTANT_RESPONSE_STYLE_VERSION, "ai_assistant_response_style.v2")
        self.assertIn("Questions are optional and are not limited to a fixed count", serialized)
        self.assertNotIn("question_dosing", serialized)
        self.assertNotIn("profile_completion_pace", serialized)
        self.assertNotIn("at most 1", serialized)
        self.assertNotIn("exactly one", serialized.lower())

    def test_numbered_question_formatter_has_no_hidden_global_cap(self):
        text = format_numbered_questions(
            ["¿Primera pregunta?", "¿Segunda pregunta?", "¿Tercera pregunta?"],
        )

        self.assertEqual(
            text,
            "1. ¿Primera pregunta?\n2. ¿Segunda pregunta?\n3. ¿Tercera pregunta?",
        )

    def test_field_specific_guidance_lives_in_typed_tool_contract(self):
        developer_payload = json.loads(self.orchestrator._developer_prompt())
        profile_tool = next(
            spec for spec in self.orchestrator.provider_tool_specs()
            if spec["name"] == TOOL_UPDATE_PROFILE_DRAFT
        )
        updates_description = profile_tool["parameters"]["properties"]["updates"]["description"]

        self.assertIn("weight_kg", updates_description)
        self.assertIn("height_cm", updates_description)
        self.assertIn("age_years", updates_description)
        self.assertIn("training_frequency", updates_description)
        self.assertNotIn("use_proposal_preferences_tools_for_goal_meals_and_targets", developer_payload["policy"])

    def test_grouped_proposal_example_keeps_complexity_in_the_function_call(self):
        developer_payload = json.loads(self.orchestrator._developer_prompt())
        grouped_example = next(
            item for item in developer_payload["operational_examples"]
            if "algo simple" in item["user_meaning"]
        )
        proposal_call = next(
            item for item in grouped_example["function_calls"]
            if TOOL_UPDATE_PROPOSAL_PREFERENCES in item
        )

        self.assertIn("meals_per_day=4", proposal_call)
        self.assertIn("complexity_level=low", proposal_call)

    def test_deterministic_question_policy_is_outside_provider_runtime_package(self):
        self.assertEqual(
            deterministic_policy.__name__,
            "notas.application.ai_intake.deterministic_policy",
        )
        self.assertTrue(hasattr(deterministic_policy, "deterministic_questions_for_brief"))
        self.assertFalse(hasattr(deterministic_policy, "build_nutrition_intake_turn_guidance"))
        self.assertFalse(hasattr(deterministic_policy, "developer_conversational_intake_policy"))
        self.assertFalse(hasattr(deterministic_policy, "nutrition_intake_field_definitions"))
