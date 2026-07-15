from __future__ import annotations

import unittest

from ai_assistant.infrastructure.providers.contracts import (
    LLMMessage,
    LLMProviderRequest,
    LLMProviderRequestError,
    LLMProviderToolOutput,
)
from ai_assistant.infrastructure.providers.openai_client import (
    OpenAIResponsesClient,
    build_openai_responses_payload,
)
from ai_assistant.management.commands.reproduce_post_tool_followup import _apply_variant


class _FakeResponse:
    """Minimal stand-in for a requests.Response with the fields the client reads."""

    def __init__(self, status_code, payload, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


class _FakeSession:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json})
        return self._response


class ProviderErrorCaptureTests(unittest.TestCase):
    """PT01: the OpenAI client preserves the provider error body instead of discarding it."""

    def _client(self, response):
        return OpenAIResponsesClient(
            api_key="test-key",
            model="test-model",
            base_url="https://example.invalid/v1",
            timeout_seconds=5,
            session=_FakeSession(response),
        )

    def _request(self):
        return LLMProviderRequest(messages=[LLMMessage(role="user", content="hola")])

    def test_preserves_structured_provider_error_body(self):
        body = {
            "error": {
                "message": "No tool output found for function call call_abc123.",
                "type": "invalid_request_error",
                "code": "tool_output_missing",
                "param": "input",
            }
        }
        client = self._client(_FakeResponse(400, body, headers={"x-request-id": "req_123"}))

        with self.assertRaises(LLMProviderRequestError) as ctx:
            client.generate(self._request())

        error = ctx.exception
        self.assertEqual(error.status_code, 400)
        self.assertEqual(error.error_type, "invalid_request_error")
        self.assertEqual(error.error_code, "tool_output_missing")
        self.assertIn("No tool output found", error.error_message)
        self.assertEqual(error.error_param, "input")
        self.assertEqual(error.request_id, "req_123")

        details = error.provider_error_details
        self.assertEqual(details["status_code"], 400)
        self.assertEqual(details["error_type"], "invalid_request_error")
        self.assertIn("No tool output found", details["error_message"])
        # The human-readable message includes the provider explanation.
        self.assertIn("No tool output found", str(error))

    def test_falls_back_to_raw_body_when_not_json(self):
        client = self._client(_FakeResponse(500, None, text="upstream boom"))

        with self.assertRaises(LLMProviderRequestError) as ctx:
            client.generate(self._request())

        error = ctx.exception
        self.assertEqual(error.status_code, 500)
        self.assertIn("upstream boom", error.error_message)

    def test_error_message_is_bounded(self):
        long_message = "x" * 5000
        body = {"error": {"message": long_message, "type": "server_error"}}
        client = self._client(_FakeResponse(503, body))

        with self.assertRaises(LLMProviderRequestError) as ctx:
            client.generate(self._request())

        self.assertLessEqual(len(ctx.exception.provider_error_details["error_message"]), 600)

    def test_payload_builder_is_shared_with_diagnostic_probe(self):
        request = LLMProviderRequest(
            messages=[LLMMessage(role="user", content="Responde con JSON")],
            max_output_tokens=123,
            metadata={
                "format": "ai_assistant_structured_response.v2",
                "response_json_schema": {
                    "type": "object",
                    "properties": {"answer": {"type": "string"}},
                    "required": ["answer"],
                    "additionalProperties": False,
                },
                "response_schema_strict": True,
                "reasoning_effort": "low",
            },
            tools=[
                {
                    "name": "read_context",
                    "description": "Read context.",
                    "parameters": {"type": "object", "properties": {}},
                }
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            continuation_items=(
                {
                    "type": "reasoning",
                    "id": "rs_1",
                    "encrypted_content": "ciphertext",
                    "summary": [],
                },
                {
                    "type": "function_call",
                    "id": "fc_1",
                    "call_id": "call_1",
                    "name": "read_context",
                    "arguments": "{}",
                    "status": "completed",
                },
            ),
            tool_outputs=(
                LLMProviderToolOutput(call_id="call_1", output={"status": "ok"}),
            ),
        )

        payload = build_openai_responses_payload(request, model="test-model")

        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertEqual(payload["reasoning"], {"effort": "low"})
        self.assertEqual(payload["tools"][0]["name"], "read_context")
        self.assertEqual(payload["input"][-1]["type"], "function_call_output")
        self.assertEqual(payload["input"][-1]["call_id"], "call_1")

    def test_probe_variants_change_the_intended_transport_dimension(self):
        request = LLMProviderRequest(
            messages=[LLMMessage(role="user", content="Responde con JSON")],
            metadata={
                "format": "ai_assistant_structured_response.v2",
                "response_json_schema": {"type": "object"},
                "response_schema_strict": True,
                "reasoning_effort": "low",
            },
            tools=[{"name": "tool", "parameters": {"type": "object"}}],
            tool_choice="auto",
            parallel_tool_calls=True,
            continuation_items=(
                {"type": "reasoning", "id": "rs_1", "encrypted_content": "cipher"},
                {"type": "function_call", "call_id": "call_1", "name": "tool", "arguments": "{}"},
            ),
        )

        non_strict = _apply_variant(
            request, strict=False, with_tools=True, with_reasoning=True
        )
        self.assertFalse(non_strict.metadata["response_schema_strict"])
        self.assertIn("response_json_schema", non_strict.metadata)

        no_tools = _apply_variant(
            request, strict=True, with_tools=False, with_reasoning=True
        )
        self.assertEqual(tuple(no_tools.tools), ())
        self.assertIsNone(no_tools.tool_choice)

        no_reasoning = _apply_variant(
            request, strict=True, with_tools=True, with_reasoning=False
        )
        self.assertNotIn("reasoning_effort", no_reasoning.metadata)
        self.assertEqual(
            [item["type"] for item in no_reasoning.continuation_items],
            ["function_call"],
        )


if __name__ == "__main__":
    unittest.main()
