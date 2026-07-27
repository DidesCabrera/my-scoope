from types import SimpleNamespace

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from email_delivery.models import EmailDeliveryAttempt
from email_delivery.services import deliver_share_invitation


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_SHARE_DELIVERY_ENABLED=True,
    EMAIL_SHARE_DAILY_BUDGET=70,
    EMAIL_SHARE_USER_DAILY_LIMIT=20,
    EMAIL_SHARE_RECIPIENT_DAILY_LIMIT=3,
    EMAIL_SHARE_RECIPIENT_COOLDOWN_SECONDS=0,
)
class ShareEmailDeliveryTests(TestCase):
    def setUp(self):
        self.sender = get_user_model().objects.create_user(
            username="sender",
            email="sender@example.com",
            password="Strong-passphrase-2026",
        )
        EmailAddress.objects.create(
            user=self.sender,
            email=self.sender.email,
            primary=True,
            verified=True,
        )

    def _share(self, *, pk, recipient="recipient@example.com", accepted_by_id=None):
        return SimpleNamespace(
            pk=pk,
            sender=self.sender,
            recipient_email=recipient,
            accepted_by_id=accepted_by_id,
            _meta=SimpleNamespace(label_lower="notas.foodshare"),
        )

    def _deliver(self, share):
        return deliver_share_invitation(
            share=share,
            subject="Compartido",
            message="Revisa tu invitación.",
            from_email="no-reply@example.com",
        )

    def test_same_share_only_sends_once(self):
        first = self._deliver(self._share(pk=101))
        second = self._deliver(self._share(pk=101))

        self.assertTrue(first.sent)
        self.assertFalse(second.sent)
        self.assertEqual(second.reason, "duplicate_share")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            EmailDeliveryAttempt.objects.filter(
                category=EmailDeliveryAttempt.CATEGORY_SHARE_INVITATION
            ).count(),
            1,
        )

    def test_existing_recipient_uses_inbox_without_email(self):
        result = self._deliver(
            self._share(pk=102, accepted_by_id=999)
        )

        self.assertFalse(result.sent)
        self.assertEqual(result.reason, "existing_recipient_inbox")
        self.assertEqual(len(mail.outbox), 0)

    def test_unverified_sender_cannot_consume_email(self):
        EmailAddress.objects.filter(user=self.sender).update(verified=False)

        result = self._deliver(self._share(pk=103))

        self.assertFalse(result.sent)
        self.assertEqual(result.reason, "sender_email_unverified")
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_SHARE_RECIPIENT_DAILY_LIMIT=1)
    def test_recipient_daily_limit_is_persistent(self):
        first = self._deliver(self._share(pk=104))
        second = self._deliver(self._share(pk=105))

        self.assertTrue(first.sent)
        self.assertFalse(second.sent)
        self.assertEqual(second.reason, "recipient_daily_limit")
        self.assertEqual(len(mail.outbox), 1)
