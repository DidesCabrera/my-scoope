import json

from django.test import SimpleTestCase, override_settings

from ai_assistant.application.orchestrator import ExternalLLMOrchestrator
from ai_assistant.application.product_context import (
    developer_product_capability_policy,
    system_domain_anchor_lines,
)
from ai_assistant.domain import AssistantMessage, AssistantMessageRole, AssistantTurnRequest
from ai_assistant.infrastructure.providers import FakeLLMClient


@override_settings(AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=False)
class ProductContextTests(SimpleTestCase):
    def test_domain_anchor_keeps_greetings_natural_and_redirects_off_domain(self):
        text = "\n".join(system_domain_anchor_lines())
        self.assertIn("saludos", text)
        self.assertIn("temas ajenos", text)
        self.assertIn("redirige", text)
        self.assertIn("dominio principal", text)

    def test_capabilities_are_expressed_as_product_outcomes(self):
        policy = developer_product_capability_policy()
        capabilities = " ".join(policy["product_capabilities"])
        self.assertIn("ficha nutricional", capabilities)
        self.assertIn("comparar planes", capabilities)
        self.assertIn("propuestas revisables", capabilities)
        self.assertTrue(policy["user_facing_explanation"]["never_disclose_function_names"])
        self.assertTrue(policy["user_facing_explanation"]["never_disclose_mcp_contracts"])

    def test_provider_prompt_separates_internal_tools_from_user_facing_capabilities(self):
        client = FakeLLMClient(responses=['{"assistant_message":{"content":"Hola"},"intent":{"name":"answer_question","confidence":0.8,"summary":"saludo"},"requires_human_review":false}'])
        orchestrator = ExternalLLMOrchestrator(llm_client=client)
        request = AssistantTurnRequest(user_message=AssistantMessage(role=AssistantMessageRole.USER, content="¿Qué puedes hacer?"))
        orchestrator.continue_turn(request)
        provider_request = client.requests[0]
        system_prompt = provider_request.messages[0].content
        developer_payload = json.loads(provider_request.messages[1].content)
        self.assertIn("no reveles nombres de functions", system_prompt)
        self.assertIn("product_context", developer_payload)
        self.assertTrue(developer_payload["policy"]["explain_capabilities_in_product_language_not_function_names"])
        self.assertIn("native_function_tools", developer_payload)
