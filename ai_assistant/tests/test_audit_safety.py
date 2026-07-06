import json

from django.test import SimpleTestCase, override_settings

from ai_assistant.application import (
    AUDIT_SCHEMA_VERSION,
    ExternalLLMOrchestrator,
    build_audit_snapshot,
    sanitize_audit_value,
)
from ai_assistant.application.tools import TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL
from ai_assistant.domain import (
    AssistantIntent,
    AssistantMessage,
    AssistantMessageRole,
    AssistantStructuredResponse,
    AssistantToolRequest,
    AssistantToolResult,
    AssistantToolStatus,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers import (
    FakeLLMClient,
    LLMProviderRequest,
    LLMProviderRequestError,
)


class FailingLLMClient:
    provider_name = "failing_fake"

    def generate(self, request: LLMProviderRequest):
        raise LLMProviderRequestError("provider failed with api_key=sk-secret-value and prompt payload")


@override_settings(AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=False)
class AIAssistantAuditSafetyTests(SimpleTestCase):
    def test_sanitize_audit_value_redacts_secrets_but_keeps_usage_metrics(self):
        sanitized = sanitize_audit_value(
            {
                "api_key": "sk-secret",
                "headers": {"Authorization": "Bearer token"},
                "provider_usage": {
                    "input_tokens": 10,
                    "output_tokens": 20,
                    "total_tokens": 30,
                },
                "nested": {"client_secret": "hidden"},
            }
        )

        self.assertEqual(sanitized["api_key"], "[redacted]")
        self.assertEqual(sanitized["headers"], "[redacted]")
        self.assertEqual(sanitized["nested"]["client_secret"], "[redacted]")
        self.assertEqual(sanitized["provider_usage"]["input_tokens"], 10)
        self.assertEqual(sanitized["provider_usage"]["output_tokens"], 20)
        self.assertEqual(sanitized["provider_usage"]["total_tokens"], 30)

    def test_audit_snapshot_records_tool_status_without_tool_arguments(self):
        response = AssistantStructuredResponse(
            assistant_message=AssistantMessage(role=AssistantMessageRole.ASSISTANT, content="Voy a validar esto."),
            intent=AssistantIntent(name="create_dailyplan_proposal", confidence=0.8, safety_flags=["review_required"]),
            tool_requests=[
                AssistantToolRequest(
                    tool_name=TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
                    request_id="call_1",
                    arguments={"nutrition_brief": {"target_kcal": 2200, "api_key": "secret"}},
                )
            ],
            tool_results=[
                AssistantToolResult(
                    tool_name=TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
                    request_id="call_1",
                    status=AssistantToolStatus.PENDING,
                    data={
                        "category": "proposal",
                        "risk_level": "review_required",
                        "requires_human_review": True,
                    },
                )
            ],
            requires_human_review=True,
        )

        audit = build_audit_snapshot(
            response=response,
            engine="external_llm_orchestrator_v1",
            provider="fake",
            provider_model="fake-llm",
            provider_usage={"input_tokens": 11, "output_tokens": 7},
            latency_ms=12,
        ).as_dict()
        serialized = json.dumps(audit, ensure_ascii=False)

        self.assertEqual(audit["version"], AUDIT_SCHEMA_VERSION)
        self.assertEqual(audit["tool_requests_count"], 1)
        self.assertEqual(audit["tool_audit"][0]["tool_name"], TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL)
        self.assertEqual(audit["tool_audit"][0]["status"], "pending")
        self.assertEqual(audit["tool_audit"][0]["risk_level"], "review_required")
        self.assertEqual(audit["provider_usage"]["input_tokens"], 11)
        self.assertNotIn("nutrition_brief", serialized)
        self.assertNotIn("target_kcal", serialized)
        self.assertNotIn("secret", serialized)

    def test_orchestrator_attaches_sanitized_audit_metadata_to_successful_turn(self):
        client = FakeLLMClient(
            responses=[
                json.dumps(
                    {
                        "assistant_message": {"content": "Prepararé una solicitud controlada."},
                        "intent": {"name": "create_dailyplan_proposal", "confidence": 0.9},
                        "tool_requests": [
                            {
                                "tool_name": TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
                                "arguments": {"nutrition_brief": {"target_kcal": 2200}},
                                "request_id": "call_1",
                            }
                        ],
                        "proposal_ids": [1234],
                        "requires_human_review": False,
                    }
                )
            ]
        )
        response = ExternalLLMOrchestrator(llm_client=client).continue_turn(
            AssistantTurnRequest(
                user_message=AssistantMessage(role=AssistantMessageRole.USER, content="Crea un plan diario"),
            )
        )

        audit = response.metadata["audit"]
        serialized = json.dumps(audit, ensure_ascii=False)

        self.assertEqual(response.metadata["audit_version"], AUDIT_SCHEMA_VERSION)
        self.assertEqual(audit["provider"], "fake")
        self.assertEqual(audit["provider_model"], "fake-llm")
        self.assertGreaterEqual(audit["latency_ms"], 0)
        self.assertEqual(audit["tool_requests_count"], 1)
        self.assertEqual(audit["ignored_provider_proposal_ids_count"], 1)
        self.assertEqual(audit["proposal_ids"], [])
        self.assertFalse(audit["tools_executed"])
        self.assertNotIn("nutrition_brief", serialized)
        self.assertNotIn("target_kcal", serialized)

    def test_orchestrator_returns_safe_audited_response_when_provider_fails(self):
        response = ExternalLLMOrchestrator(llm_client=FailingLLMClient()).continue_turn(
            AssistantTurnRequest(
                user_message=AssistantMessage(role=AssistantMessageRole.USER, content="Hola"),
            )
        )
        audit = response.metadata["audit"]
        serialized = json.dumps(response.metadata, ensure_ascii=False)

        self.assertIn("sin aplicar cambios", response.assistant_text)
        self.assertTrue(response.requires_human_review)
        self.assertEqual(response.metadata["provider_error_code"], "llm_provider_error")
        self.assertEqual(audit["error_code"], "llm_provider_error")
        self.assertEqual(audit["error_type"], "LLMProviderRequestError")
        self.assertEqual(audit["provider"], "failing_fake")
        self.assertFalse(audit["tools_executed"])
        self.assertNotIn("sk-secret-value", serialized)
        self.assertNotIn("prompt payload", serialized)
