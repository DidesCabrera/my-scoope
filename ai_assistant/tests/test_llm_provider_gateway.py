from django.test import SimpleTestCase, override_settings

from ai_assistant.infrastructure.providers import (
    FakeLLMClient,
    LLMMessage,
    LLMProviderConfigurationError,
    LLMProviderRequest,
    LLMProviderRequestError,
    LLMProviderToolOutput,
    OpenAIResponsesClient,
    get_llm_client,
)
from ai_assistant.infrastructure.providers.openai_client import (
    OPENAI_RESPONSES_PATH,
    build_openai_responses_payload,
)


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


    def test_openai_payload_preserves_case_sensitive_function_call_id(self):
        request = LLMProviderRequest(
            messages=[LLMMessage(role="user", content="Usa la herramienta")],
            continuation_items=(
                {
                    "type": "function_call",
                    "id": "fc_1",
                    "call_id": "call_AbC123XyZ",
                    "name": "update_proposal_preferences",
                    "arguments": "{}",
                    "status": "completed",
                },
            ),
            tool_outputs=(
                LLMProviderToolOutput(
                    call_id="call_AbC123XyZ",
                    output={"status": "ok"},
                ),
            ),
        )

        payload = build_openai_responses_payload(request, model="gpt-test")

        self.assertEqual(payload["input"][-1]["call_id"], "call_AbC123XyZ")

    def test_openai_payload_rejects_case_mismatched_function_output_before_http(self):
        request = LLMProviderRequest(
            messages=[LLMMessage(role="user", content="Usa la herramienta")],
            continuation_items=(
                {
                    "type": "function_call",
                    "id": "fc_1",
                    "call_id": "call_AbC123XyZ",
                    "name": "update_proposal_preferences",
                    "arguments": "{}",
                    "status": "completed",
                },
            ),
            tool_outputs=(
                LLMProviderToolOutput(
                    call_id="call_abc123xyz",
                    output={"status": "ok"},
                ),
            ),
        )

        with self.assertRaisesMessage(
            LLMProviderRequestError,
            "missing outputs for ['call_AbC123XyZ']",
        ):
            build_openai_responses_payload(request, model="gpt-test")

    def test_fake_client_rejects_case_mismatched_function_output(self):
        client = FakeLLMClient(responses=["No debería generarse."])
        request = LLMProviderRequest(
            messages=[LLMMessage(role="user", content="Usa la herramienta")],
            continuation_items=(
                {
                    "type": "function_call",
                    "id": "fc_1",
                    "call_id": "call_AbC123XyZ",
                    "name": "update_proposal_preferences",
                    "arguments": "{}",
                    "status": "completed",
                },
            ),
            tool_outputs=(
                LLMProviderToolOutput(
                    call_id="call_abc123xyz",
                    output={"status": "ok"},
                ),
            ),
        )

        with self.assertRaisesMessage(
            LLMProviderRequestError,
            "missing outputs for ['call_AbC123XyZ']",
        ):
            client.generate(request)

        self.assertEqual(client.requests, [])

    def test_fake_client_rejects_reasoning_without_encrypted_content(self):
        client = FakeLLMClient(responses=["No debería generarse."])
        request = LLMProviderRequest(
            messages=[LLMMessage(role="user", content="Usa la herramienta")],
            continuation_items=(
                {
                    "type": "reasoning",
                    "id": "rs_missing_encrypted",
                    "summary": [],
                    "status": "completed",
                },
                {
                    "type": "function_call",
                    "id": "fc_1",
                    "call_id": "call_AbC123XyZ",
                    "name": "update_proposal_preferences",
                    "arguments": "{}",
                    "status": "completed",
                },
            ),
            tool_outputs=(
                LLMProviderToolOutput(
                    call_id="call_AbC123XyZ",
                    output={"status": "ok"},
                ),
            ),
        )

        with self.assertRaisesMessage(
            LLMProviderRequestError,
            "encrypted_content is required",
        ):
            client.generate(request)

        self.assertEqual(client.requests, [])

    def test_openai_payload_rejects_reasoning_without_encrypted_content(self):
        request = LLMProviderRequest(
            messages=[LLMMessage(role="user", content="Continúa")],
            continuation_items=(
                {
                    "type": "reasoning",
                    "id": "rs_1",
                    "summary": [],
                    "status": "completed",
                },
            ),
        )

        with self.assertRaisesMessage(
            LLMProviderRequestError,
            "encrypted_content is required",
        ):
            build_openai_responses_payload(request, model="gpt-test")

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
        self.assertEqual(call["json"]["include"], ["reasoning.encrypted_content"])
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
    def test_openai_client_uses_strict_json_schema_and_reasoning_whitelist(self):
        session = StubSession(
            StubResponse(
                payload={
                    "id": "resp_structured",
                    "model": "gpt-test",
                    "output_text": '{"format":"ai_assistant_structured_response.v2"}',
                }
            )
        )
        client = OpenAIResponsesClient(session=session)
        schema = {
            "type": "object",
            "properties": {"format": {"type": "string"}},
            "required": ["format"],
            "additionalProperties": False,
        }

        client.generate(
            LLMProviderRequest(
                messages=[LLMMessage(role="user", content="Hola")],
                max_output_tokens=1400,
                metadata={
                    "format": "ai_assistant_structured_response.v2",
                    "response_json_schema": schema,
                    "response_schema_name": "ai_assistant_structured_response",
                    "response_schema_strict": True,
                    "reasoning_effort": "low",
                    "private_debug_value": "must-not-leak",
                },
            )
        )

        payload = session.calls[0]["json"]
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertEqual(payload["text"]["format"]["name"], "ai_assistant_structured_response")
        self.assertEqual(payload["text"]["format"]["schema"], schema)
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertEqual(payload["text"]["verbosity"], "low")
        self.assertEqual(payload["reasoning"], {"effort": "low"})
        self.assertNotIn("private_debug_value", payload)

    @override_settings(
        AI_ASSISTANT_OPENAI_API_KEY="sk-test",
        AI_ASSISTANT_OPENAI_MODEL="gpt-test",
        AI_ASSISTANT_OPENAI_BASE_URL="https://api.openai.com/v1",
    )
    def test_openai_client_uses_native_function_tools_and_extracts_calls(self):
        session = StubSession(
            StubResponse(
                payload={
                    "id": "resp_tool_1",
                    "model": "gpt-test",
                    "output": [
                        {
                            "type": "reasoning",
                            "id": "rs_1",
                            "encrypted_content": "encrypted-reasoning",
                            "summary": [],
                            "status": "completed",
                        },
                        {
                            "type": "function_call",
                            "id": "fc_1",
                            "call_id": "call_1",
                            "name": "update_proposal_preferences",
                            "arguments": '{"updates":{"goal":"fat_loss"}}',
                            "status": "completed",
                        },
                    ],
                }
            )
        )
        client = OpenAIResponsesClient(session=session)

        response = client.generate(
            LLMProviderRequest(
                messages=[LLMMessage(role="user", content="Quiero bajar grasa")],
                tools=(
                    {
                        "name": "update_proposal_preferences",
                        "description": "Update proposal preferences.",
                        "parameters": {
                            "type": "object",
                            "properties": {"updates": {"type": "object"}},
                            "required": ["updates"],
                        },
                    },
                ),
                tool_choice="auto",
                parallel_tool_calls=True,
                max_tool_calls=3,
            )
        )

        payload = session.calls[0]["json"]
        self.assertEqual(payload["tools"][0]["type"], "function")
        self.assertEqual(payload["tools"][0]["name"], "update_proposal_preferences")
        self.assertFalse(payload["tools"][0]["strict"])
        self.assertEqual(payload["tool_choice"], "auto")
        self.assertTrue(payload["parallel_tool_calls"])
        self.assertNotIn("max_tool_calls", payload)
        self.assertEqual(response.text, "")
        self.assertEqual(response.tool_calls[0].call_id, "call_1")
        self.assertEqual(response.tool_calls[0].arguments["updates"]["goal"], "fat_loss")
        self.assertEqual(response.continuation_items[0]["type"], "reasoning")
        self.assertEqual(response.continuation_items[1]["type"], "function_call")

    @override_settings(
        AI_ASSISTANT_OPENAI_API_KEY="sk-test",
        AI_ASSISTANT_OPENAI_MODEL="gpt-test",
        AI_ASSISTANT_OPENAI_BASE_URL="https://api.openai.com/v1",
    )
    def test_openai_client_returns_function_outputs_in_stateless_continuation(self):
        session = StubSession(
            StubResponse(
                payload={
                    "id": "resp_final_2",
                    "model": "gpt-test",
                    "output_text": '{"assistant_message":{"content":"Listo"}}',
                }
            )
        )
        client = OpenAIResponsesClient(session=session)

        client.generate(
            LLMProviderRequest(
                messages=[LLMMessage(role="user", content="Quiero bajar grasa")],
                continuation_items=(
                    {
                        "type": "reasoning",
                        "id": "rs_1",
                        "encrypted_content": "encrypted-reasoning",
                        "summary": [],
                        "status": "completed",
                    },
                    {
                        "type": "function_call",
                        "id": "fc_1",
                        "call_id": "call_1",
                        "name": "update_proposal_preferences",
                        "arguments": '{"updates":{"goal":"fat_loss"}}',
                        "status": "completed",
                    },
                ),
                tool_outputs=(
                    LLMProviderToolOutput(
                        call_id="call_1",
                        output={"status": "ok", "data": {"goal": "fat_loss"}},
                    ),
                ),
            )
        )

        input_items = session.calls[0]["json"]["input"]
        self.assertEqual(input_items[0]["role"], "user")
        self.assertEqual(input_items[1]["type"], "reasoning")
        self.assertEqual(input_items[2]["type"], "function_call")
        self.assertEqual(input_items[3]["type"], "function_call_output")
        self.assertEqual(input_items[3]["call_id"], "call_1")
        self.assertIn('"status": "ok"', input_items[3]["output"])

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
