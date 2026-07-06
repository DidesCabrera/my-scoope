from django.test import SimpleTestCase

from ai_assistant.application.chat_engines import ChatEngineRequest
from ai_assistant.application.context_builder import (
    build_safe_llm_context,
    merge_safe_context_into_request,
    sanitize_provider_context,
)
from notas.application.ai_intake.nutrition_brief import start_or_continue_conversation


class SafeLLMContextBuilderTests(SimpleTestCase):
    def test_builds_minimal_context_from_nutrition_conversation_state(self):
        request = ChatEngineRequest(
            message="Quiero un plan de 2100 kcal con 4 comidas y 160g de proteína",
            existing_payload={"raw": "session payload must not be forwarded"},
            user_id=123,
        )
        state = start_or_continue_conversation(
            message=request.normalized_message,
            existing_payload=request.existing_payload,
        )

        context = build_safe_llm_context(request, conversation_state=state).as_dict()

        self.assertEqual(context["surface"], "ai_nutrition_intake")
        self.assertEqual(context["user"], {"authenticated": True, "id_present": True})
        self.assertTrue(context["conversation"]["existing_payload_present"])
        self.assertGreaterEqual(context["conversation"]["message_count"], 2)
        self.assertEqual(context["nutrition_brief"]["calorie_target"], 2100)
        self.assertEqual(context["nutrition_brief"]["meals_per_day"], 4)
        self.assertFalse(context["runtime"]["tools_enabled"])
        self.assertFalse(context["runtime"]["proposal_creation_enabled"])
        self.assertEqual(context["metadata"]["context_builder"], "safe_llm_context.v1")

    def test_context_does_not_forward_identity_or_raw_payload_values(self):
        request = ChatEngineRequest(
            message="hola",
            existing_payload={"api_key": "secret", "email": "felipe@example.com"},
            user_id=999,
        )

        context_text = str(build_safe_llm_context(request).as_dict())

        self.assertNotIn("999", context_text)
        self.assertNotIn("secret", context_text)
        self.assertNotIn("felipe@example.com", context_text)
        self.assertIn("id_present", context_text)
        self.assertIn("existing_payload_present", context_text)

    def test_sanitizes_extra_context_and_sensitive_keys(self):
        safe = sanitize_provider_context(
            {
                "surface": "ai_assistant",
                "authorization_header": "Bearer secret-token",
                "profile_email": "felipe@example.com",
                "nested": {"csrf_token": "secret", "safe_hint": "ok"},
                "long_text": "x" * 400,
            }
        )

        self.assertEqual(safe["surface"], "ai_assistant")
        self.assertNotIn("authorization_header", safe)
        self.assertNotIn("profile_email", safe)
        self.assertNotIn("csrf_token", safe["nested"])
        self.assertEqual(safe["nested"]["safe_hint"], "ok")
        self.assertLessEqual(len(safe["long_text"]), 241)

    def test_merge_safe_context_into_request_keeps_payload_out_of_metadata(self):
        request = ChatEngineRequest(
            message="hola",
            existing_payload={"raw": "session"},
            metadata={"surface": "ai_nutrition_intake"},
        )
        safe_context = build_safe_llm_context(request)

        merged = merge_safe_context_into_request(request, safe_context=safe_context)

        self.assertEqual(merged.existing_payload, request.existing_payload)
        self.assertIn("safe_llm_context", merged.metadata)
        self.assertNotIn("raw", str(merged.metadata["safe_llm_context"]))
        self.assertEqual(merged.metadata["safe_llm_context_version"], "safe_llm_context.v1")
