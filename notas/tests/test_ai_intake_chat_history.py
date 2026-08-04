from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notas.application.ai_intake.chat_history import AI_NUTRITION_CHAT_SESSION_KEY
from notas.application.ai_intake.deterministic_chat_engine import (
    DeterministicNutritionIntakeChatEngine,
)
from notas.application.ai_intake.nutrition_brief import (
    AI_NUTRITION_BRIEF_SESSION_KEY,
    AI_NUTRITION_CONVERSATION_SESSION_KEY,
)
from notas.domain.models import AiNutritionChat, Food, NutritionProposal


class AiNutritionChatHistoryTests(TestCase):
    def setUp(self):
        self.engine_patcher = patch(
            "notas.interface.views.ai_intake.get_nutrition_intake_chat_engine",
            return_value=DeterministicNutritionIntakeChatEngine(),
        )
        self.engine_patcher.start()
        self.addCleanup(self.engine_patcher.stop)
        self.user = User.objects.create_user(username="felipe", password="testpass123")
        profile = self.user.profile
        profile.onboarding_completed_at = timezone.now()
        profile.onboarding_version = profile.ONBOARDING_VERSION_NUTRITION_V1
        profile.save(update_fields=["onboarding_completed_at", "onboarding_version"])
        self.client.force_login(self.user)

    def test_home_uses_compact_ai_composer_without_copy_or_visible_hero(self):
        response = self.client.get(reverse("home_view"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn("home-ai-intake__copy", html)
        self.assertIn('class="home-hero main" hidden', html)
        self.assertIn('class="home-ai-intake home-ai-intake--composer"', html)
        self.assertIn('class="home-ai-intake__form"', html)
        self.assertIn('placeholder="Pídeme lo que necesites"', html)
        self.assertIn('name="action" value="analyze_prompt"', html)
        self.assertIn("Necesito una dieta.", html)
        self.assertIn("Comparar Alimentos", html)
        self.assertIn("Quiero reemplazar mi comida", html)
        self.assertIn("Necesito reducir las calorias de mi dieta", html)
        self.assertIn("Quiero ajustar la composicion de mis comidas", html)
        self.assertIn('data-lucide="chevron-down"', html)
        self.assertIn("home-ai-intake__quick-form--desktop", html)
        self.assertIn("home-ai-intake__more-form--mobile", html)

    def test_home_quick_tabs_start_ai_chat_with_expected_prompts(self):
        expected_prompts = [
            "Hola! Necesito una dieta.",
            "Hola! Me gustaría comparar Alimentos",
            "Quiero reemplazar mi comida.",
            "Necesito reducir las calorias de mi dieta.",
            "Quiero ajustar la composicion de mis comidas.",
        ]

        for prompt in expected_prompts:
            with self.subTest(prompt=prompt):
                response = self.client.post(
                    reverse("ai_nutrition_intake"),
                    {
                        "action": "analyze_prompt",
                        "prompt": prompt,
                    },
                )

                self.assertRedirects(response, reverse("ai_nutrition_intake"))
                self.assertTrue(
                    AiNutritionChat.objects.filter(
                        user=self.user,
                        conversation_payload__messages__0__text=prompt,
                    ).exists()
                )

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


    def test_chat_list_renders_history_metadata_and_new_chat_action(self):
        self.client.post(
            reverse("ai_nutrition_intake"),
            {
                "action": "analyze_prompt",
                "prompt": (
                    "Quiero bajar grasa con 4 comidas simple. "
                    "Peso 80 kg, altura 175 cm, tengo 30 años, hombre, actividad moderada."
                ),
            },
        )
        chat = AiNutritionChat.objects.get(user=self.user)

        response = self.client.get(reverse("ai_nutrition_chat_list"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn(reverse("ai_nutrition_chat_new"), html)
        self.assertIn("Nuevo chat", html)
        self.assertIn("ai-chat-history-card--active", html)
        self.assertIn(chat.title, html)
        self.assertIn("Bajar grasa", html)
        self.assertIn("4 comidas/día", html)
        self.assertIn("2 mensajes", html)
        self.assertIn("Brief listo", html)

    def test_new_chat_action_clears_only_active_session(self):
        self.client.post(
            reverse("ai_nutrition_intake"),
            {
                "action": "analyze_prompt",
                "prompt": "Quiero bajar grasa con 4 comidas y algo simple.",
            },
        )
        chat = AiNutritionChat.objects.get(user=self.user)
        self.assertEqual(self.client.session[AI_NUTRITION_CHAT_SESSION_KEY], chat.id)

        response = self.client.get(reverse("ai_nutrition_chat_new"))

        self.assertRedirects(response, reverse("ai_nutrition_intake"))
        self.assertEqual(AiNutritionChat.objects.filter(user=self.user).count(), 1)
        self.assertNotIn(AI_NUTRITION_CHAT_SESSION_KEY, self.client.session)
        self.assertNotIn(AI_NUTRITION_CONVERSATION_SESSION_KEY, self.client.session)
        self.assertNotIn(AI_NUTRITION_BRIEF_SESSION_KEY, self.client.session)

    def test_create_proposal_generates_dailyplan_card_inside_chat(self):
        self._create_minimal_food_catalog()
        self.client.post(
            reverse("ai_nutrition_intake"),
            {
                "action": "analyze_prompt",
                "prompt": (
                    "Quiero bajar grasa con 4 comidas y algo simple. "
                    "Peso 80 kg, altura 175 cm, tengo 30 años, hombre, actividad moderada."
                ),
            },
        )

        response = self.client.post(
            reverse("ai_nutrition_intake"),
            {"action": "create_proposal"},
        )

        self.assertRedirects(response, reverse("ai_nutrition_intake"))
        chat = AiNutritionChat.objects.get(user=self.user)
        self.assertEqual(chat.status, AiNutritionChat.STATUS_PROPOSAL_CREATED)
        self.assertIsNotNone(chat.proposal)
        self.assertEqual(chat.proposal.proposed_payload["intent"], "create_dailyplan")
        self.assertEqual(NutritionProposal.objects.filter(created_by=self.user).count(), 2)
        self.assertIn(AI_NUTRITION_CONVERSATION_SESSION_KEY, self.client.session)

        page_response = self.client.get(reverse("ai_nutrition_intake"))
        html = page_response.content.decode()
        self.assertIn("ai-generated-plan-card--current", html)
        self.assertIn("Propuesta actual", html)
        self.assertIn("Propuesta concreta generada", html)
        self.assertIn("Ver detalle de la propuesta", html)
        self.assertIn(reverse("proposal_detail", args=[chat.proposal.id]), html)

        list_response = self.client.get(reverse("ai_nutrition_chat_list"))
        list_html = list_response.content.decode()
        self.assertIn("Ver propuesta asociada", list_html)
        self.assertIn(reverse("proposal_detail", args=[chat.proposal.id]), list_html)
        self.assertIn("Propuesta creada", list_html)

    def _create_minimal_food_catalog(self):
        Food.objects.create(
            name="Pechuga de pollo",
            protein=31,
            carbs=0,
            fat=3,
            created_by=None,
            is_global=True,
            is_verified=True,
            food_group="carnes",
            data_quality_score=95,
            default_portion_g=170,
            min_portion_g=90,
            max_portion_g=260,
            portion_step_g=5,
        )
        Food.objects.create(
            name="Arroz cocido",
            protein=2.7,
            carbs=28,
            fat=0.3,
            created_by=None,
            is_global=True,
            is_verified=True,
            food_group="cereales",
            data_quality_score=90,
            default_portion_g=150,
            min_portion_g=45,
            max_portion_g=240,
            portion_step_g=5,
        )
        Food.objects.create(
            name="Palta",
            protein=2,
            carbs=9,
            fat=15,
            created_by=None,
            is_global=True,
            is_verified=True,
            food_group="grasas",
            data_quality_score=80,
            default_portion_g=30,
            min_portion_g=10,
            max_portion_g=40,
            portion_step_g=5,
        )
        Food.objects.create(
            name="Tomate",
            protein=1,
            carbs=4,
            fat=0.2,
            created_by=None,
            is_global=True,
            is_verified=True,
            food_group="verduras",
            data_quality_score=80,
            default_portion_g=100,
            min_portion_g=50,
            max_portion_g=180,
            portion_step_g=5,
        )
