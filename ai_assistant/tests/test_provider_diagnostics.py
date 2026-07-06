from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from ai_assistant.application.provider_diagnostics import diagnose_llm_provider
from ai_assistant.infrastructure.providers import (
    FakeLLMClient,
    LLMMessage,
    LLMProviderRequest,
    LLMProviderRequestError,
    LLMProviderResponse,
)


class FailingLLMClient:
    provider_name = "fake"

    def generate(self, request: LLMProviderRequest) -> LLMProviderResponse:
        raise LLMProviderRequestError("Provider failed with status 429 and no secret payload.")


class ProviderDiagnosticsTests(SimpleTestCase):
    @override_settings(AI_ASSISTANT_LLM_PROVIDER="fake")
    def test_fake_provider_is_diagnostic_ok_without_live_call(self):
        result = diagnose_llm_provider()

        self.assertEqual(result.provider, "fake")
        self.assertTrue(result.configured)
        self.assertTrue(result.client_buildable)
        self.assertEqual(result.live_check, "skipped")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.missing_settings, ())
        self.assertEqual(result.model, "fake-llm")

    @override_settings(AI_ASSISTANT_LLM_PROVIDER="unsupported")
    def test_unsupported_provider_returns_configuration_error(self):
        result = diagnose_llm_provider()

        self.assertEqual(result.provider, "unsupported")
        self.assertFalse(result.configured)
        self.assertFalse(result.client_buildable)
        self.assertEqual(result.status, "configuration_error")
        self.assertEqual(result.missing_settings, ("AI_ASSISTANT_LLM_PROVIDER",))
        self.assertIn("Unsupported AI_ASSISTANT_LLM_PROVIDER", result.error_message)

    @override_settings(
        AI_ASSISTANT_LLM_PROVIDER="openai",
        AI_ASSISTANT_OPENAI_API_KEY="",
        AI_ASSISTANT_OPENAI_MODEL="gpt-test",
        AI_ASSISTANT_OPENAI_BASE_URL="https://api.openai.com/v1",
    )
    def test_openai_provider_reports_missing_api_key_without_secret_values(self):
        result = diagnose_llm_provider()

        self.assertEqual(result.provider, "openai")
        self.assertFalse(result.configured)
        self.assertFalse(result.client_buildable)
        self.assertEqual(result.live_check, "skipped")
        self.assertEqual(result.status, "configuration_error")
        self.assertEqual(result.missing_settings, ("AI_ASSISTANT_OPENAI_API_KEY",))
        self.assertEqual(result.model, "gpt-test")
        self.assertTrue(result.base_url_configured)
        self.assertNotIn("https://api.openai.com", str(result.as_dict()))

    @override_settings(AI_ASSISTANT_LLM_PROVIDER="fake")
    def test_live_diagnostic_uses_minimal_fake_request(self):
        client = FakeLLMClient(responses=["OK"])

        result = diagnose_llm_provider(live=True, client_factory=lambda provider: client)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.live_check, "ok")
        self.assertEqual(result.live_response_provider, "fake")
        self.assertEqual(result.live_response_model, "fake-llm")
        self.assertEqual(result.live_response_id, "fake-response-1")
        self.assertEqual(len(client.requests), 1)
        request = client.requests[0]
        self.assertEqual(request.max_output_tokens, 16)
        self.assertEqual(request.metadata, {"diagnostic": True})
        self.assertEqual(
            [message.role for message in request.normalized_messages],
            ["developer", "user"],
        )
        self.assertIn("diagnostic", request.normalized_messages[1].content.lower())

    @override_settings(AI_ASSISTANT_LLM_PROVIDER="fake")
    def test_live_provider_failure_is_safe_provider_error(self):
        result = diagnose_llm_provider(live=True, client_factory=lambda provider: FailingLLMClient())

        self.assertTrue(result.configured)
        self.assertTrue(result.client_buildable)
        self.assertEqual(result.live_check, "failed")
        self.assertEqual(result.status, "provider_error")
        self.assertIn("status 429", result.error_message)
        self.assertNotIn("Authorization", str(result.as_dict()))
        self.assertNotIn("api_key", str(result.as_dict()).lower())

    @override_settings(AI_ASSISTANT_LLM_PROVIDER="fake")
    def test_management_command_prints_safe_summary(self):
        from io import StringIO

        output = StringIO()
        call_command("diagnose_ai_assistant_llm", stdout=output)

        rendered = output.getvalue()
        self.assertIn("AI Assistant LLM diagnostics", rendered)
        self.assertIn("provider: fake", rendered)
        self.assertIn("configured: true", rendered)
        self.assertIn("live_check: skipped", rendered)
        self.assertIn("status: ok", rendered)
        self.assertNotIn("API_KEY", rendered)
        self.assertNotIn("Authorization", rendered)

    def test_provider_diagnostics_do_not_import_operational_or_catalog_domains(self):
        import ai_assistant.application.provider_diagnostics as provider_diagnostics

        self.assertNotIn("food_catalog", provider_diagnostics.__dict__)
        self.assertNotIn("Food", provider_diagnostics.__dict__)
        self.assertNotIn("DailyPlan", provider_diagnostics.__dict__)
        self.assertNotIn("NutritionProposal", provider_diagnostics.__dict__)
