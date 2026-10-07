from django.test import override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import AiNutritionChat


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIAssistantMessageFormattingTests(AuthenticatedMobileAPITestCase):
    def test_ai_chat_preserves_assistant_markdown_and_line_breaks(self):
        formatted = "## Resumen\n\n- **Proteína:** 130 g\n- Carbohidratos: 340 g"
        chat = AiNutritionChat.objects.create(
            user=self.user,
            conversation_payload={"messages": [{"role": "assistant", "text": formatted}]},
        )

        response = self.client.get(f"/api/v1/ai/chats/{chat.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["messages"][0]["text"], formatted)
