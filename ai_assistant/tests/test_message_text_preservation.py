from django.test import SimpleTestCase

from ai_assistant.domain import AssistantMessage
from ai_assistant.domain.message_text import normalize_visible_message_content
from ai_assistant.infrastructure.providers import LLMMessage, LLMProviderRequest, LLMProviderResponse


class VisibleMessageTextPreservationTests(SimpleTestCase):
    formatted = "## Resumen\n\n- **Primero:** valor\n- Segundo\n\n1. Revisar\n2. Confirmar"

    def test_visible_message_normalization_preserves_markdown_blocks(self):
        self.assertEqual(normalize_visible_message_content(self.formatted), self.formatted)

    def test_domain_contract_preserves_markdown_blocks(self):
        message = AssistantMessage(role="assistant", content=self.formatted)

        self.assertEqual(message.content, self.formatted)

    def test_provider_request_history_preserves_markdown_blocks(self):
        request = LLMProviderRequest(messages=[LLMMessage(role="assistant", content=self.formatted)])

        self.assertEqual(request.normalized_messages[0].content, self.formatted)

    def test_provider_response_preserves_markdown_blocks(self):
        response = LLMProviderResponse(provider="test", model="test", text=self.formatted)

        self.assertEqual(response.normalized_text, self.formatted)

    def test_normalization_bounds_whitespace_without_flattening_lines(self):
        raw = "  Encabezado  \r\n\r\n\r\n-   Elemento   con   espacios  "

        self.assertEqual(normalize_visible_message_content(raw), "Encabezado\n\n- Elemento con espacios")
