from django.test import SimpleTestCase, override_settings

from ai_assistant.infrastructure.providers import (
    FakeLLMClient,
    LLMMessage,
    LLMProviderConfigurationError,
    LLMProviderRequest,
    LLMProviderRequestError,
    OpenAIResponsesClient,
    get_llm_client,
)
from ai_assistant.infrastructure.providers.openai_client import OPENAI_RESPONSES_PATH


class StubResponse:
    def __init__(self, *, status_code=200, payload=None, invalid_json=False):
        self.status_code = status_code
        self.payload = payload or {}
        self.invalid_json = invalid_json

    def json(self):
        if self.invalid_json:
            raise ValueError("invalid json")
        return self.payload


class StubSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, *, json, headers, timeout):
        self.calls.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return self.response


class LLMProviderGatewayTests(SimpleTestCase):
    def test_fake_client_records_normalized_request_and_returns_scripted_response(self):
        client = FakeLLMClient(responses=["  Listo.  "])
        response = client.generate(
            LLMProviderRequest(
                messages=[LLMMessage(role="user", content="  quiero   un plan  ")],
                metadata={"internal": "not-forwarded"},
            )
        )

        self.assertEqual(response.provider, "fake")
        self.assertEqual(response.normalized_text, "Listo.")
        self.assertEqual(client.requests[0].messages[0].content, "quiero un plan")
        self.assertEqual(client.requests[0].metadata["internal"], "not-forwarded")

    def test_fake_client_builds_default_response_from_last_user_message(self):
        client = FakeLLMClient()
        response = client.generate(
            LLMProviderRequest(
                messages=[
                    LLMMessage(role="developer", content="Responde breve."),
                    LLMMessage(role="user", content="Necesito una comida alta en proteína"),
                ]
            )
        )

        self.assertIn("Necesito una comida alta en proteína", response.text)

    @override_settings(AI_ASSISTANT_LLM_PROVIDER="fake")
    def test_factory_returns_fake_client(self):
        self.assertIsInstance(get_llm_client(), FakeLLMClient)

    @override_settings(AI_ASSISTANT_LLM_PROVIDER="unsupported")
    def test_factory_rejects_unknown_provider(self):
        with self.assertRaises(LLMProviderConfigurationError):
            get_llm_client()

    @override_settings(
        AI_ASSISTANT_OPENAI_API_KEY="",
        AI_ASSISTANT_OPENAI_MODEL="gpt-test",
        AI_ASSISTANT_OPENAI_BASE_URL="https://api.openai.com/v1",
    )
    def test_openai_client_fails_controlled_without_api_key(self):
        client = OpenAIResponsesClient(session=StubSession(StubResponse()))

        with self.assertRaisesMessage(
            LLMProviderConfigurationError,
            "AI_ASSISTANT_OPENAI_API_KEY is not configured.",
        ):
            client.generate(LLMProviderRequest(messages=[LLMMessage(role="user", content="Hola")]))

    @override_settings(
        AI_ASSISTANT_OPENAI_API_KEY="sk-test",
        AI_ASSISTANT_OPENAI_MODEL="gpt-test",
        AI_ASSISTANT_OPENAI_BASE_URL="https://api.openai.com/v1/",
        AI_ASSISTANT_OPENAI_TIMEOUT_SECONDS=7,
    )
    def test_openai_client_posts_minimal_responses_payload(self):
        session = StubSession(
            StubResponse(
                payload={
                    "id": "resp_123",
                    "model": "gpt-test",
                    "output_text": "Hola desde OpenAI",
                    "usage": {"input_tokens": 10, "output_tokens": 4},
                }
            )
        )
        client = OpenAIResponsesClient(session=session)

        response = client.generate(
            LLMProviderRequest(
                messages=[
                    LLMMessage(role="developer", content="Usa contexto mínimo."),
                    LLMMessage(role="user", content="  crea una propuesta  "),
                ],
                max_output_tokens=120,
                metadata={"chat_id": 123, "must_not_leave_app": True},
            )
        )

        call = session.calls[0]
        self.assertEqual(call["url"], f"https://api.openai.com/v1{OPENAI_RESPONSES_PATH}")
        self.assertEqual(call["timeout"], 7)
        self.assertEqual(call["headers"]["Authorization"], "Bearer sk-test")
        self.assertEqual(call["json"]["model"], "gpt-test")
        self.assertEqual(call["json"]["store"], False)
        self.assertEqual(call["json"]["max_output_tokens"], 120)
        self.assertEqual(
            call["json"]["input"],
            [
                {"role": "developer", "content": "Usa contexto mínimo."},
                {"role": "user", "content": "crea una propuesta"},
            ],
        )
        self.assertNotIn("metadata", call["json"])
        self.assertEqual(response.text, "Hola desde OpenAI")
        self.assertEqual(response.response_id, "resp_123")
        self.assertEqual(response.usage["input_tokens"], 10)

    @override_settings(
        AI_ASSISTANT_OPENAI_API_KEY="sk-test",
        AI_ASSISTANT_OPENAI_MODEL="gpt-test",
        AI_ASSISTANT_OPENAI_BASE_URL="https://api.openai.com/v1",
    )
    def test_openai_client_extracts_text_from_output_content(self):
        session = StubSession(
            StubResponse(
                payload={
                    "id": "resp_456",
                    "output": [
                        {
                            "content": [
                                {"type": "output_text", "text": "Primera línea."},
                                {"type": "output_text", "text": "Segunda línea."},
                            ]
                        }
                    ],
                }
            )
        )
        client = OpenAIResponsesClient(session=session)

        response = client.generate(
            LLMProviderRequest(messages=[LLMMessage(role="user", content="Hola")])
        )

        self.assertEqual(response.text, "Primera línea.\nSegunda línea.")

    @override_settings(
        AI_ASSISTANT_OPENAI_API_KEY="sk-test",
        AI_ASSISTANT_OPENAI_MODEL="gpt-test",
        AI_ASSISTANT_OPENAI_BASE_URL="https://api.openai.com/v1",
    )
    def test_openai_client_raises_sanitized_error_on_provider_failure(self):
        client = OpenAIResponsesClient(session=StubSession(StubResponse(status_code=429)))

        with self.assertRaisesMessage(
            LLMProviderRequestError,
            "OpenAI provider request failed with status 429.",
        ):
            client.generate(LLMProviderRequest(messages=[LLMMessage(role="user", content="Hola")]))

    def test_provider_gateway_does_not_import_food_catalog(self):
        import ai_assistant.infrastructure.providers.contracts as contracts
        import ai_assistant.infrastructure.providers.fake_client as fake_client
        import ai_assistant.infrastructure.providers.openai_client as openai_client

        self.assertNotIn("food_catalog", contracts.__dict__)
        self.assertNotIn("food_catalog", fake_client.__dict__)
        self.assertNotIn("food_catalog", openai_client.__dict__)
