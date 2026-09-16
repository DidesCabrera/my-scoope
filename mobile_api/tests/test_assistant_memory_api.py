from django.test import override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import AiNutritionChat, NutritionPreferenceProfile


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIAssistantMemoryTests(AuthenticatedMobileAPITestCase):
    def test_preference_card_requires_explicit_mobile_commit_before_persistence(self):
        chat = AiNutritionChat.objects.create(
            user=self.user,
            title="Preferencias",
            conversation_payload={
                "brief": {
                    "raw_prompt": "Prefiero tofu y soy vegano",
                    "dietary_pattern": "vegan",
                    "preferred_foods": ["tofu"],
                    "field_sources": {
                        "dietary_pattern": "chat_draft",
                        "preferred_foods": "chat_draft",
                    },
                },
                "messages": [
                    {"role": "user", "text": "Prefiero tofu y soy vegano"},
                    {
                        "role": "assistant",
                        "text": "Puedes revisar estas preferencias.",
                        "preference_draft_card": {
                            "title": "Preferencias",
                            "known_count": 2,
                            "can_update_preferences": True,
                            "sections": [
                                {
                                    "title": "Alimentación",
                                    "items": [
                                        {"key": "dietary_pattern", "label": "Patrón", "value": "Vegano"},
                                        {"key": "preferred_foods", "label": "Preferidos", "value": "tofu"},
                                    ],
                                }
                            ],
                        },
                    },
                ],
            },
        )
        self.assertFalse(NutritionPreferenceProfile.objects.filter(user=self.user).exists())

        detail = self.client.get(f"/api/v1/ai/chats/{chat.id}")
        preference_card = detail.json()["data"]["messages"][1]["cards"][0]
        self.assertTrue(preference_card["can_commit"])

        committed = self.client.post(f"/api/v1/ai/chats/{chat.id}/preferences/commit")

        self.assertEqual(committed.status_code, 200)
        self.assertEqual(committed.json()["data"]["status"], "updated")
        stored = NutritionPreferenceProfile.objects.get(user=self.user)
        self.assertEqual(stored.preferences["dietary_pattern"], "vegan")
        self.assertEqual(stored.preferences["preferred_foods"], ["tofu"])
