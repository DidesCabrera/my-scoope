from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from notas.application.ai_intake.chat_history import AI_NUTRITION_CHAT_SESSION_KEY
from notas.application.ai_intake.nutrition_brief import (
    AI_NUTRITION_BRIEF_SESSION_KEY,
    AI_NUTRITION_CONVERSATION_SESSION_KEY,
)
from notas.domain.models import AiNutritionChat


class AiNutritionChatHistoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="felipe", password="testpass123")
        self.client.force_login(self.user)

    def test_home_uses_compact_ai_composer_without_copy_or_visible_hero(self):
        response = self.client.get(reverse("home_view"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn("home-ai-intake__copy", html)
        self.assertIn('class="home-hero main" hidden', html)
        self.assertIn('class="home-ai-intake home-ai-intake--composer"', html)
        self.assertIn('class="home-ai-intake__form"', html)
        self.assertIn('placeholder="¿En qué puedo ayudarte?"', html)
        self.assertIn('name="action" value="analyze_prompt"', html)

    def test_analyze_prompt_persists_chat_history(self):
        response = self.client.post(
            reverse("ai_nutrition_intake"),
            {
                "action": "analyze_prompt",
                "prompt": "Quiero bajar grasa con 4 comidas y algo simple.",
            },
        )

        self.assertRedirects(response, reverse("ai_nutrition_intake"))
        chat = AiNutritionChat.objects.get(user=self.user)
        self.assertIn("bajar grasa", chat.title.lower())
        self.assertEqual(chat.status, AiNutritionChat.STATUS_ACTIVE)
        self.assertTrue(chat.conversation_payload.get("messages"))
        self.assertEqual(self.client.session[AI_NUTRITION_CHAT_SESSION_KEY], chat.id)
        self.assertIn(AI_NUTRITION_CONVERSATION_SESSION_KEY, self.client.session)
        self.assertIn(AI_NUTRITION_BRIEF_SESSION_KEY, self.client.session)

    def test_continue_conversation_updates_same_chat(self):
        self.client.post(
            reverse("ai_nutrition_intake"),
            {
                "action": "analyze_prompt",
                "prompt": "Quiero bajar grasa.",
            },
        )
        chat = AiNutritionChat.objects.get(user=self.user)

        response = self.client.post(
            reverse("ai_nutrition_intake"),
            {
                "action": "continue_conversation",
                "is_async": "1",
                "message": "4 comidas y algo simple.",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AiNutritionChat.objects.filter(user=self.user).count(), 1)
        chat.refresh_from_db()
        messages = chat.conversation_payload.get("messages") or []
        self.assertTrue(any(item.get("text") == "4 comidas y algo simple." for item in messages))
        self.assertEqual(self.client.session[AI_NUTRITION_CHAT_SESSION_KEY], chat.id)

    def test_chat_list_and_detail_render_saved_conversation(self):
        self.client.post(
            reverse("ai_nutrition_intake"),
            {
                "action": "analyze_prompt",
                "prompt": "Quiero bajar grasa con 4 comidas y algo simple.",
            },
        )
        chat = AiNutritionChat.objects.get(user=self.user)

        list_response = self.client.get(reverse("ai_nutrition_chat_list"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Chats")
        self.assertContains(list_response, chat.title)

        detail_response = self.client.get(reverse("ai_nutrition_chat_detail", args=[chat.id]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Quiero bajar grasa")
        self.assertEqual(self.client.session[AI_NUTRITION_CHAT_SESSION_KEY], chat.id)
