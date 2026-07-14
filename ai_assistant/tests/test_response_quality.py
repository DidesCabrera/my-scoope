import json

from django.test import SimpleTestCase

from ai_assistant.application.orchestrator import (
    ExternalLLMOrchestrator,
    _local_acknowledgement_from_tool_results,
)
from ai_assistant.application.response_style import (
    ASSISTANT_RESPONSE_STYLE_VERSION,
    developer_response_style_policy,
    system_response_style_lines,
)
from ai_assistant.application.tools import (
    TOOL_SHARE_PROFILE_DRAFT_CARD,
    TOOL_UPDATE_PROFILE_DRAFT,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
)
from ai_assistant.domain import AssistantToolResult, AssistantToolStatus
from ai_assistant.infrastructure.providers import FakeLLMClient


class ResponseQualityPolicyTests(SimpleTestCase):
    def setUp(self):
        self.orchestrator = ExternalLLMOrchestrator(llm_client=FakeLLMClient(responses=[]))

    def test_response_style_v3_treats_cards_as_visible_and_avoids_recitation(self):
        system_policy = "\n".join(system_response_style_lines())
        developer_policy = developer_response_style_policy()
        serialized = json.dumps(developer_policy, ensure_ascii=False)

        self.assertEqual(ASSISTANT_RESPONSE_STYLE_VERSION, "ai_assistant_response_style.v3")
        self.assertIn("cards ya son visibles", system_policy)
        self.assertIn("sin recitar sus campos", system_policy)
        self.assertIn("sin recitar payloads ni datos recién entregados", system_policy)
        self.assertIn("visible cards as known", serialized)
        self.assertIn("Explain tool consequences", serialized)
        self.assertIn("do not echo inputs or stock acknowledgements", serialized)

    def test_provider_prompt_contains_ba05_without_exact_copy_templates(self):
        system_prompt = self.orchestrator._system_prompt()
        developer_payload = json.loads(self.orchestrator._developer_prompt())
        serialized = json.dumps(developer_payload, ensure_ascii=False)

        self.assertIn("Tras una tool", system_prompt)
        self.assertIn("response_style_policy", developer_payload)
        self.assertEqual(
            developer_payload["response_style_policy"]["version"],
            "ai_assistant_response_style.v3",
        )
        self.assertNotIn("response_templates", serialized)
        self.assertNotIn("exact_phrase", serialized)

    def test_compact_tool_followup_marks_cards_visible_without_expanding_main_prompt(self):
        payload = json.loads(
            self.orchestrator._compact_tool_results_prompt(
                (
                    AssistantToolResult(
                        tool_name=TOOL_SHARE_PROFILE_DRAFT_CARD,
                        status=AssistantToolStatus.OK,
                        data={"profile_draft_card": {"title": "Ficha"}},
                    ),
                )
            )
        )

        self.assertTrue(payload["policy"]["cards_are_visible"])
        self.assertTrue(payload["policy"]["do_not_echo_fields"])
        self.assertTrue(payload["policy"]["explain_consequence_not_payload"])

    def test_local_profile_ack_reports_state_without_echoing_values_or_stock_opener(self):
        acknowledgement = _local_acknowledgement_from_tool_results(
            (
                AssistantToolResult(
                    tool_name=TOOL_UPDATE_PROFILE_DRAFT,
                    status=AssistantToolStatus.OK,
                    data={
                        "profile_draft": {
                            "weight_kg": 85,
                            "height_cm": 188,
                            "age_years": 38,
                        }
                    },
                ),
            )
        )

        self.assertEqual(
            acknowledgement,
            "Los datos físicos quedaron actualizados para esta conversación.",
        )
        self.assertNotIn("Perfecto", acknowledgement)
        self.assertNotIn("85", acknowledgement)
        self.assertNotIn("188", acknowledgement)
        self.assertNotIn("38", acknowledgement)
        self.assertNotIn("?", acknowledgement)

    def test_local_card_ack_orients_to_card_without_repeating_payload(self):
        acknowledgement = _local_acknowledgement_from_tool_results(
            (
                AssistantToolResult(
                    tool_name=TOOL_SHARE_PROFILE_DRAFT_CARD,
                    status=AssistantToolStatus.OK,
                    data={
                        "profile_draft_card": {
                            "title": "Ficha para esta propuesta",
                            "items": [
                                {"label": "Peso", "value": "85 kg"},
                                {"label": "Altura", "value": "188 cm"},
                            ],
                        }
                    },
                ),
            )
        )

        self.assertEqual(
            acknowledgement,
            "La información está disponible en la card para revisión.",
        )
        self.assertNotIn("85", acknowledgement)
        self.assertNotIn("188", acknowledgement)

    def test_local_proposal_preferences_ack_reports_consequence_not_inputs(self):
        acknowledgement = _local_acknowledgement_from_tool_results(
            (
                AssistantToolResult(
                    tool_name=TOOL_UPDATE_PROPOSAL_PREFERENCES,
                    status=AssistantToolStatus.OK,
                    data={
                        "proposal_preferences": {
                            "goal": "fat_loss",
                            "requested_entity": "program",
                            "meals_per_day": 3,
                        }
                    },
                ),
            )
        )

        self.assertEqual(acknowledgement, "La dirección de la propuesta quedó actualizada.")
        self.assertNotIn("bajar grasa", acknowledgement)
        self.assertNotIn("programa", acknowledgement)
        self.assertNotIn("3 comidas", acknowledgement)
