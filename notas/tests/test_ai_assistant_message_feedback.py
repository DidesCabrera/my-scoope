from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notas.application.ai_intake.chat_history import sync_chat_from_conversation
from notas.application.ai_intake.message_feedback import (
    record_message_feedback,
    summarize_message_feedback,
)
from notas.application.ai_intake.nutrition_brief import start_or_continue_conversation
from notas.domain.models import AiAssistantMessageFeedback, Profile


class AiAssistantMessageFeedbackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="feedback", password="pass123")
        self.user.profile.onboarding_completed_at = timezone.now()
        self.user.profile.onboarding_version = Profile.ONBOARDING_VERSION_NUTRITION_V1
        self.user.profile.save(
            update_fields=["onboarding_completed_at", "onboarding_version"]
        )
        self.conversation = start_or_continue_conversation(message="Quiero bajar grasa")
        self.chat = sync_chat_from_conversation(
            user=self.user,
            conversation=self.conversation,
        )
        self.assistant_index = next(
            index
            for index, message in enumerate(self.conversation.messages)
            if message.role == "assistant" and message.text
        )

    def test_feedback_is_scoped_to_one_visible_assistant_message_and_upserts(self):
        feedback = record_message_feedback(
            user=self.user,
            chat=self.chat,
            message_index=self.assistant_index,
            rating="helpful",
        )
        updated = record_message_feedback(
            user=self.user,
            chat=self.chat,
            message_index=self.assistant_index,
            rating="not_helpful",
            reason="ignored_context",
            comment="Ya había entregado ese dato.",
        )

        self.assertEqual(feedback.id, updated.id)
        self.assertEqual(AiAssistantMessageFeedback.objects.count(), 1)
        self.assertEqual(updated.rating, "not_helpful")
        self.assertEqual(updated.reason, "ignored_context")
        self.assertEqual(len(updated.response_fingerprint), 64)

    def test_user_message_cannot_be_rated_as_assistant_output(self):
        user_index = next(
            index
            for index, message in enumerate(self.conversation.messages)
            if message.role == "user"
        )

        with self.assertRaisesMessage(ValueError, "feedback_message_not_rateable"):
            record_message_feedback(
                user=self.user,
                chat=self.chat,
                message_index=user_index,
                rating="helpful",
            )

    def test_feedback_endpoint_is_owner_scoped_and_renders_controls(self):
        self.client.force_login(self.user)
        detail = self.client.get(
            reverse("ai_nutrition_chat_detail", args=[self.chat.id])
        )
        feedback_url = reverse(
            "ai_assistant_message_feedback",
            args=[self.chat.id, self.assistant_index],
        )

        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "¿Te sirvió?")
        self.assertContains(detail, feedback_url)

        response = self.client.post(feedback_url, {"rating": "helpful"})

        self.assertRedirects(
            response,
            reverse("ai_nutrition_chat_detail", args=[self.chat.id]),
        )
        self.assertTrue(
            AiAssistantMessageFeedback.objects.filter(
                user=self.user,
                chat=self.chat,
                message_index=self.assistant_index,
                rating="helpful",
            ).exists()
        )

        other = User.objects.create_user(username="other", password="pass123")
        other.profile.onboarding_completed_at = timezone.now()
        other.profile.onboarding_version = Profile.ONBOARDING_VERSION_NUTRITION_V1
        other.profile.save(
            update_fields=["onboarding_completed_at", "onboarding_version"]
        )
        self.client.force_login(other)
        denied = self.client.post(feedback_url, {"rating": "not_helpful"})
        self.assertEqual(denied.status_code, 404)

    def test_aggregate_report_excludes_message_content_and_comments(self):
        record_message_feedback(
            user=self.user,
            chat=self.chat,
            message_index=self.assistant_index,
            rating="not_helpful",
            reason="unclear",
            comment="Texto privado que no debe salir.",
        )

        report = summarize_message_feedback(days=30)

        self.assertEqual(report["total"], 1)
        self.assertEqual(report["not_helpful"], 1)
        self.assertEqual(report["reason_counts"], {"unclear": 1})
        self.assertFalse(report["contains_message_content"])
        self.assertFalse(report["contains_comments"])
        self.assertNotIn("Texto privado", str(report))
