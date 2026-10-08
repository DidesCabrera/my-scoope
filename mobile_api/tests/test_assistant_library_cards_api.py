from django.test import override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import AiNutritionChat


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIAssistantLibraryCardTests(AuthenticatedMobileAPITestCase):
    def test_ai_chat_projects_library_and_comparison_card_references(self):
        chat = AiNutritionChat.objects.create(
            user=self.user,
            title="Biblioteca visible",
            conversation_payload={
                "messages": [
                    {
                        "role": "assistant",
                        "text": "Estos son tus objetos.",
                        "created_at": "2026-10-07T20:10:00-03:00",
                        "library_cards": [
                            {"resource": "programs", "entity": "program", "item_id": 12, "title": "Programa fuerza"},
                            {"resource": "foods", "entity": "food", "item_id": 13, "title": "Avena"},
                        ],
                        "saved_comparison_cards": [
                            {"comparison_id": 14, "kind": "foods", "title": "Proteínas"},
                        ],
                    }
                ]
            },
        )

        response = self.client.get(f"/api/v1/ai/chats/{chat.id}")

        self.assertEqual(response.status_code, 200)
        message = response.json()["data"]["messages"][0]
        self.assertEqual(
            [card["type"] for card in message["cards"]], ["library_item", "library_item", "saved_comparison"]
        )
        self.assertEqual(message["cards"][0]["resource"], "programs")
        self.assertEqual(message["cards"][2]["comparison_id"], 14)
        self.assertEqual(message["created_at"], "2026-10-07T20:10:00-03:00")
