from dataclasses import replace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import CreditWallet
from accounts.seed_plans import seed_account_plans
from billing.application.contracts import AppleNotificationEvidence, AppleTransactionEvidence
from billing.application.services.apple_app_store import (
    get_or_create_apple_app_account_token,
    process_apple_notification,
)
from billing.application.services.credit_packs import (
    CreditPackUnavailable,
    configure_credit_pack_product,
    refund_apple_credit_pack,
    settle_apple_credit_pack,
)
from billing.application.services.events import receive_verified_billing_event
from billing.models import CreditPackPurchase, PaymentProvider


class AppleCreditPackLifecycleTests(TestCase):
    def setUp(self):
        seed_account_plans()
        self.user = get_user_model().objects.create_user(username="apple-pack-lifecycle")
        self.product = configure_credit_pack_product(provider="apple_app_store", environment="sandbox",
            offer_code="credits-500", external_product_id="pack.apple")
        token = get_or_create_apple_app_account_token(self.user)
        self.evidence = AppleTransactionEvidence(original_transaction_id="original-pack", transaction_id="pack-1",
            product_id=self.product.external_product_id, app_account_token=str(token.token), environment="Sandbox",
            ownership_type="PURCHASED")

    def event(self, kind):
        return receive_verified_billing_event(provider=PaymentProvider.APPLE_APP_STORE, external_event_id=kind,
            event_type=kind, signature_verified=True).event

    def test_refund_before_purchase_prevents_late_credit_grant(self):
        refund_apple_credit_pack(user=self.user, evidence=self.evidence)
        purchase = settle_apple_credit_pack(user=self.user, evidence=self.evidence)
        self.assertEqual(purchase.status, "refunded")
        self.assertEqual(purchase.credits_granted, 0)
        self.assertFalse(CreditWallet.objects.filter(user=self.user).exists())

    def test_webhook_and_device_delivery_credit_once_then_refund_once(self):
        notification = AppleNotificationEvidence(notification_uuid="pack-event", notification_type="ONE_TIME_CHARGE",
            environment="Sandbox", transaction=self.evidence)
        event = self.event("ONE_TIME_CHARGE")
        process_apple_notification(event=event, notification=notification)
        process_apple_notification(event=event, notification=notification)
        settle_apple_credit_pack(user=self.user, evidence=self.evidence)
        self.assertEqual(CreditWallet.objects.get(user=self.user).purchased_balance, 500)
        refund = self.event("REFUND")
        process_apple_notification(event=refund, notification=replace(notification, notification_type="REFUND"))
        process_apple_notification(event=refund, notification=replace(notification, notification_type="REFUND"))
        self.assertEqual(CreditWallet.objects.get(user=self.user).purchased_balance, 0)
        self.assertEqual(CreditPackPurchase.objects.count(), 1)

    def test_inactive_mapping_still_settles_an_existing_store_receipt(self):
        self.product.active = False
        self.product.save(update_fields=["active"])
        self.assertEqual(settle_apple_credit_pack(user=self.user, evidence=self.evidence).credits_granted, 500)

    def test_a_verified_revoked_receipt_is_acknowledged_as_refunded_without_granting(self):
        purchase = settle_apple_credit_pack(user=self.user, evidence=replace(self.evidence, revocation_date=timezone.now()))
        self.assertEqual(purchase.status, "refunded")
        self.assertFalse(CreditWallet.objects.filter(user=self.user).exists())

    def test_the_same_consumable_can_be_purchased_again_with_a_new_transaction(self):
        settle_apple_credit_pack(user=self.user, evidence=self.evidence)
        settle_apple_credit_pack(user=self.user, evidence=replace(self.evidence, transaction_id="pack-2"))
        self.assertEqual(CreditWallet.objects.get(user=self.user).purchased_balance, 1000)
        self.assertEqual(CreditPackPurchase.objects.count(), 2)

    def test_a_refund_after_account_deletion_updates_evidence_without_recreating_a_wallet(self):
        from accounts.services.deletion import delete_user_account
        settle_apple_credit_pack(user=self.user, evidence=self.evidence)
        delete_user_account(user=self.user, source="test_apple_refund")
        self.user.refresh_from_db()
        self.assertFalse(CreditWallet.objects.filter(user=self.user).exists())
        refunded = refund_apple_credit_pack(user=self.user, evidence=self.evidence)
        self.assertEqual(refunded.status, "refunded")
        self.assertFalse(CreditWallet.objects.filter(user=self.user).exists())

    def test_a_late_new_purchase_cannot_recreate_a_deleted_accounts_wallet(self):
        from accounts.services.deletion import delete_user_account
        delete_user_account(user=self.user, source="test_late_apple_purchase")
        # The caller still holds its pre-deletion User instance; settlement must
        # reload the account under its lock rather than trust that old instance.
        with self.assertRaises(CreditPackUnavailable):
            settle_apple_credit_pack(user=self.user, evidence=self.evidence)
        self.assertFalse(CreditWallet.objects.filter(user=self.user).exists())
        self.assertFalse(CreditPackPurchase.objects.filter(user=self.user).exists())
