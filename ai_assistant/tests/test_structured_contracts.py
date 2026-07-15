from django.test import SimpleTestCase

from ai_assistant.domain import (
    AssistantContractError,
    AssistantIntent,
    AssistantIntentName,
    AssistantMessage,
    AssistantMessageRole,
    AssistantStructuredResponse,
    AssistantToolRequest,
    AssistantToolResult,
    AssistantToolStatus,
    AssistantTurnRequest,
)


class AssistantStructuredContractsTests(SimpleTestCase):
    def test_message_normalizes_content_name_and_metadata(self):
        message = AssistantMessage(
            role="user",
            content="  Necesito   un plan   simple  ",
            name="  Intake Surface  ",
            metadata={"chat_id": 12},
        )

        self.assertEqual(message.role, AssistantMessageRole.USER)
        self.assertEqual(message.normalized_content, "Necesito un plan simple")
        self.assertEqual(message.name, "intake_surface")
        self.assertEqual(
            message.as_dict(),
            {
                "role": "user",
                "content": "Necesito un plan simple",
                "name": "intake_surface",
                "metadata": {"chat_id": 12},
            },
        )

    def test_message_rejects_empty_content(self):
        with self.assertRaisesMessage(AssistantContractError, "AssistantMessage requires non-empty content."):
            AssistantMessage(role="user", content="   ")

    def test_intent_normalizes_and_marks_write_intents(self):
        intent = AssistantIntent(
            name="create_dailyplan_proposal",
            confidence="0.8",
            summary="  Crear   plan diario  ",
            slots={"meals_per_day": 4},
            missing_slots=[" calorie target "],
            safety_flags=["needs review"],
        )

        self.assertEqual(intent.name, AssistantIntentName.CREATE_DAILYPLAN_PROPOSAL)
        self.assertEqual(intent.confidence, 0.8)
        self.assertEqual(intent.summary, "Crear plan diario")
        self.assertEqual(intent.missing_slots, ("calorie_target",))
        self.assertEqual(intent.safety_flags, ("needs_review",))
        self.assertTrue(intent.is_write_intent)
        self.assertTrue(intent.requires_clarification)

    def test_intent_rejects_invalid_confidence(self):
        with self.assertRaisesMessage(AssistantContractError, "confidence must be between 0 and 1"):
            AssistantIntent(confidence=1.5)

    def test_turn_request_requires_user_message_and_preserves_history(self):
        system_message = AssistantMessage(role="system", content="Usa tools controladas.")
        user_message = AssistantMessage(role="user", content="Hazme un plan")
        request = AssistantTurnRequest(
            user_message=user_message,
            history=[system_message],
            context={"surface": "ai_intake"},
        )

        self.assertEqual(request.messages, (system_message, user_message))
        self.assertEqual(request.as_dict()["context"], {"surface": "ai_intake"})

    def test_turn_request_rejects_non_user_current_message(self):
        with self.assertRaisesMessage(AssistantContractError, "AssistantTurnRequest requires a user message."):
            AssistantTurnRequest(user_message=AssistantMessage(role="assistant", content="Listo."))

    def test_tool_request_and_result_contracts_are_serializable(self):
        tool_request = AssistantToolRequest(
            tool_name="  Create DailyPlan Proposal  ",
            arguments={"brief_id": 99},
            request_id="  call_AbC123  ",
            reason="  Crear propuesta revisable  ",
        )
        tool_result = AssistantToolResult(
            tool_name="create_dailyplan_proposal",
            status="ok",
            data={"proposal_id": 123},
            request_id="call_AbC123",
        )

        self.assertEqual(tool_request.tool_name, "create_dailyplan_proposal")
        self.assertEqual(tool_request.request_id, "call_AbC123")
        self.assertEqual(tool_result.request_id, "call_AbC123")
        self.assertEqual(tool_request.as_dict()["arguments"], {"brief_id": 99})
        self.assertEqual(tool_result.status, AssistantToolStatus.OK)
        self.assertTrue(tool_result.ok)
        self.assertEqual(tool_result.as_dict()["data"], {"proposal_id": 123})

    def test_error_tool_result_requires_error_details(self):
        with self.assertRaisesMessage(
            AssistantContractError,
            "Error or blocked tool results require error_code or error_message.",
        ):
            AssistantToolResult(tool_name="safe_tool", status="error")

    def test_structured_response_defaults_to_human_review_boundary(self):
        response = AssistantStructuredResponse(
            assistant_message=AssistantMessage(role="assistant", content="Creé una propuesta para revisión."),
            intent=AssistantIntent(name="create_dailyplan_proposal", confidence=0.9),
            tool_requests=[AssistantToolRequest(tool_name="create_dailyplan_proposal")],
            proposal_ids=[123],
            metadata={"engine": "llm_v1"},
        )

        payload = response.as_dict()
        self.assertEqual(response.assistant_text, "Creé una propuesta para revisión.")
        self.assertTrue(response.has_tool_requests)
        self.assertTrue(response.has_proposals)
        self.assertTrue(response.requires_human_review)
        self.assertEqual(payload["proposal_ids"], [123])
        self.assertEqual(payload["intent"]["name"], "create_dailyplan_proposal")
        self.assertEqual(payload["tool_requests"][0]["tool_name"], "create_dailyplan_proposal")

    def test_structured_response_requires_assistant_message(self):
        with self.assertRaisesMessage(
            AssistantContractError,
            "AssistantStructuredResponse requires an assistant message.",
        ):
            AssistantStructuredResponse(
                assistant_message=AssistantMessage(role="user", content="Hazme un plan"),
            )

    def test_structured_contracts_do_not_import_operational_or_provider_domains(self):
        import ai_assistant.domain.contracts as contracts

        self.assertNotIn("food_catalog", contracts.__dict__)
        self.assertNotIn("notas", contracts.__dict__)
        self.assertNotIn("infrastructure", contracts.__dict__)
