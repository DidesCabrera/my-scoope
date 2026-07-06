from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notas.application.ai_intake.nutrition_brief import (
    AI_NUTRITION_BRIEF_SESSION_KEY,
    AI_NUTRITION_CONVERSATION_SESSION_KEY,
    build_intake_result,
    start_or_continue_conversation,
)
from notas.domain.models import Profile


def complete_onboarding_for_test_user(user):
    profile = user.profile
    profile.onboarding_completed_at = timezone.now()
    profile.onboarding_version = Profile.ONBOARDING_VERSION_NUTRITION_V1
    profile.save(update_fields=["onboarding_completed_at", "onboarding_version"])


class NutritionBriefParsingTests(TestCase):
    def test_bajar_grasa_sets_fat_loss_and_does_not_ask_goal(self):
        result = build_intake_result("bajar grasa")

        self.assertEqual(result.brief.goal, "fat_loss")
        self.assertNotIn(
            "¿Cuál es tu objetivo principal: bajar grasa, ganar masa, mantenerte o mejorar rendimiento?",
            result.required_follow_up_questions,
        )

    def test_fat_loss_is_detected_with_accented_and_free_phrasing(self):
        result = build_intake_result("Quiero una dieta para pérdida de grasa y definición")

        self.assertEqual(result.brief.goal, "fat_loss")
        self.assertNotIn("objetivo principal", " ".join(result.required_follow_up_questions).lower())


class NutritionConversationStateTests(TestCase):
    def test_conversation_accumulates_goal_meals_and_style(self):
        state = start_or_continue_conversation(message="bajar grasa")
        state = start_or_continue_conversation(
            message="4 comidas simple peso 80 kg altura 175 cm tengo 30 años hombre actividad moderada",
            existing_payload={
                "brief": {
                    "raw_prompt": state.result.brief.raw_prompt,
                    "goal": state.result.brief.goal,
                    "requested_entity": state.result.brief.requested_entity,
                    "meals_per_day": state.result.brief.meals_per_day,
                    "training_frequency": state.result.brief.training_frequency,
                    "calorie_target": state.result.brief.calorie_target,
                    "protein_target": state.result.brief.protein_target,
                    "carb_target": state.result.brief.carb_target,
                    "fat_target": state.result.brief.fat_target,
                    "style_preferences": state.result.brief.style_preferences,
                    "excluded_foods": state.result.brief.excluded_foods,
                    "preferred_foods": state.result.brief.preferred_foods,
                    "complexity_level": state.result.brief.complexity_level,
                    "budget_level": state.result.brief.budget_level,
                    "notes": state.result.brief.notes,
                },
                "messages": [
                    {"role": message.role, "text": message.text}
                    for message in state.messages
                ],
            },
        )

        self.assertEqual(state.result.brief.goal, "fat_loss")
        self.assertEqual(state.result.brief.meals_per_day, 4)
        self.assertIn("simple", state.result.brief.style_preferences)
        self.assertTrue(state.is_ready_for_proposal)
        self.assertNotIn("Cuál es tu objetivo", state.messages[-1].text)

    def test_conversation_repairs_missing_goal_from_existing_raw_prompt(self):
        corrupted_existing_payload = {
            "brief": {
                "raw_prompt": "bajar grasa",
                "goal": None,
                "requested_entity": "daily_plan",
                "style_preferences": [],
                "excluded_foods": [],
                "preferred_foods": [],
                "notes": [],
            },
            "messages": [
                {"role": "user", "text": "bajar grasa"},
                {
                    "role": "assistant",
                    "text": "Perfecto. Para preparar una primera propuesta, me falta esto: 1. ¿Cuál es tu objetivo principal?",
                },
            ],
        }

        state = start_or_continue_conversation(
            message="4 comidas simple peso 80 kg altura 175 cm tengo 30 años hombre actividad moderada",
            existing_payload=corrupted_existing_payload,
        )

        self.assertEqual(state.result.brief.goal, "fat_loss")
        self.assertEqual(state.result.brief.meals_per_day, 4)
        self.assertIn("simple", state.result.brief.style_preferences)
        self.assertNotIn("Cuál es tu objetivo", state.messages[-1].text)


class AiNutritionIntakeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@example.com",
            password="pass123",
        )
        complete_onboarding_for_test_user(self.user)
        self.client.force_login(self.user)
        self.url = reverse("ai_nutrition_intake")

    def test_initial_prompt_persists_goal_and_does_not_ask_goal_again(self):
        response = self.client.post(
            self.url,
            {"action": "analyze_prompt", "prompt": "bajar grasa"},
        )

        self.assertEqual(response.status_code, 302)
        session = self.client.session
        brief_payload = session[AI_NUTRITION_BRIEF_SESSION_KEY]
        conversation_payload = session[AI_NUTRITION_CONVERSATION_SESSION_KEY]

        self.assertEqual(brief_payload["goal"], "fat_loss")
        self.assertNotIn("Cuál es tu objetivo", conversation_payload["messages"][-1]["text"])

    def test_async_continue_updates_same_session_and_thread_html(self):
        self.client.post(
            self.url,
            {"action": "analyze_prompt", "prompt": "bajar grasa"},
        )

        response = self.client.post(
            self.url,
            {
                "action": "continue_conversation",
                "is_async": "1",
                "message": "4 comidas simple peso 80 kg altura 175 cm tengo 30 años hombre actividad moderada",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        session = self.client.session
        brief_payload = session[AI_NUTRITION_BRIEF_SESSION_KEY]

        self.assertEqual(brief_payload["goal"], "fat_loss")
        self.assertEqual(brief_payload["meals_per_day"], 4)
        self.assertIn("simple", brief_payload["style_preferences"])
        self.assertNotIn("Cuál es tu objetivo", payload["thread_html"])
        self.assertTrue(payload["is_ready_for_proposal"])


class NutritionBriefReadyCardTests(TestCase):
    def test_completed_summary_items_exclude_pending_or_empty_fields(self):
        result = build_intake_result("bajar grasa 4 comidas simple peso 80 kg altura 175 cm tengo 30 años hombre actividad moderada")

        labels = [item.label for item in result.completed_summary_items]
        values = [item.value for item in result.completed_summary_items]

        self.assertTrue(result.is_ready_for_proposal)
        self.assertIn("Objetivo", labels)
        self.assertIn("Tipo de solución", labels)
        self.assertIn("Comidas por día", labels)
        self.assertIn("Preferencias", labels)
        self.assertNotIn("Entrenamiento", labels)
        self.assertNotIn("Kcal objetivo", labels)
        self.assertNotIn("Proteína objetivo", labels)
        self.assertNotIn("Exclusiones", labels)
        self.assertNotIn("Pendiente", values)
        self.assertNotIn("Sin exclusiones detectadas", values)

    def test_explicit_brief_request_keeps_ready_brief_and_reply_mentions_card(self):
        state = start_or_continue_conversation(message="bajar grasa")
        state = start_or_continue_conversation(
            message="4 comidas simple peso 80 kg altura 175 cm tengo 30 años hombre actividad moderada",
            existing_payload={
                "brief": {
                    "raw_prompt": state.result.brief.raw_prompt,
                    "goal": state.result.brief.goal,
                    "requested_entity": state.result.brief.requested_entity,
                    "meals_per_day": state.result.brief.meals_per_day,
                    "training_frequency": state.result.brief.training_frequency,
                    "calorie_target": state.result.brief.calorie_target,
                    "protein_target": state.result.brief.protein_target,
                    "carb_target": state.result.brief.carb_target,
                    "fat_target": state.result.brief.fat_target,
                    "style_preferences": state.result.brief.style_preferences,
                    "excluded_foods": state.result.brief.excluded_foods,
                    "preferred_foods": state.result.brief.preferred_foods,
                    "complexity_level": state.result.brief.complexity_level,
                    "budget_level": state.result.brief.budget_level,
                    "notes": state.result.brief.notes,
                },
                "messages": [
                    {"role": message.role, "text": message.text}
                    for message in state.messages
                ],
            },
        )
        state = start_or_continue_conversation(
            message="quiero ver el brief",
            existing_payload={
                "brief": {
                    "raw_prompt": state.result.brief.raw_prompt,
                    "goal": state.result.brief.goal,
                    "requested_entity": state.result.brief.requested_entity,
                    "meals_per_day": state.result.brief.meals_per_day,
                    "training_frequency": state.result.brief.training_frequency,
                    "calorie_target": state.result.brief.calorie_target,
                    "protein_target": state.result.brief.protein_target,
                    "carb_target": state.result.brief.carb_target,
                    "fat_target": state.result.brief.fat_target,
                    "style_preferences": state.result.brief.style_preferences,
                    "excluded_foods": state.result.brief.excluded_foods,
                    "preferred_foods": state.result.brief.preferred_foods,
                    "complexity_level": state.result.brief.complexity_level,
                    "budget_level": state.result.brief.budget_level,
                    "notes": state.result.brief.notes,
                },
                "messages": [
                    {"role": message.role, "text": message.text}
                    for message in state.messages
                ],
            },
        )

        self.assertTrue(state.is_ready_for_proposal)
        self.assertIn("te dejo el brief", state.messages[-1].text.lower())
        self.assertEqual(state.result.brief.goal, "fat_loss")
        self.assertEqual(state.result.brief.meals_per_day, 4)
        self.assertIn("simple", state.result.brief.style_preferences)


class AiNutritionIntakeBriefCardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="briefcard",
            email="briefcard@example.com",
            password="pass123",
        )
        complete_onboarding_for_test_user(self.user)
        self.client.force_login(self.user)
        self.url = reverse("ai_nutrition_intake")

    def test_ready_async_thread_renders_brief_card_with_create_proposal_button(self):
        self.client.post(
            self.url,
            {"action": "analyze_prompt", "prompt": "bajar grasa"},
        )

        response = self.client.post(
            self.url,
            {
                "action": "continue_conversation",
                "is_async": "1",
                "message": "4 comidas simple peso 80 kg altura 175 cm tengo 30 años hombre actividad moderada",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        html = payload["thread_html"]

        self.assertTrue(payload["is_ready_for_proposal"])
        self.assertIn("Brief listo", html)
        self.assertIn("Crear propuesta", html)
        self.assertNotIn("ai-chat-brief-card__optional", html)
        self.assertIn("Bajar grasa", html)
        self.assertIn("Comidas por día", html)
        self.assertIn("Simple", html)
        self.assertNotIn("Pendiente", html)
        self.assertNotIn("Sin exclusiones detectadas", html)
        self.assertNotIn("Kcal objetivo", html)

    def test_ver_brief_async_request_renders_ready_card_without_losing_state(self):
        self.client.post(
            self.url,
            {"action": "analyze_prompt", "prompt": "bajar grasa"},
        )
        self.client.post(
            self.url,
            {
                "action": "continue_conversation",
                "is_async": "1",
                "message": "4 comidas simple peso 80 kg altura 175 cm tengo 30 años hombre actividad moderada",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        response = self.client.post(
            self.url,
            {
                "action": "continue_conversation",
                "is_async": "1",
                "message": "quiero ver el brief",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        html = payload["thread_html"]
        session = self.client.session
        brief_payload = session[AI_NUTRITION_BRIEF_SESSION_KEY]

        self.assertTrue(payload["is_ready_for_proposal"])
        self.assertEqual(brief_payload["goal"], "fat_loss")
        self.assertEqual(brief_payload["meals_per_day"], 4)
        self.assertIn("simple", brief_payload["style_preferences"])
        self.assertIn("quiero ver el brief", html)
        self.assertIn("Brief listo", html)
        self.assertIn("Crear propuesta", html)
        self.assertIn("te dejo el brief", html.lower())
