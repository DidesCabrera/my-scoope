"""Behavioral regressions for delivery order and Apple subscription lifecycle."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import AccountSubscription
from billing.application.services.apple_app_store import AppleEvidenceError, sync_apple_transaction
from billing.models import BillingProduct, PaymentProvider, ProviderSubscription
from billing.tests import test_apple_app_store


class AppleLifecycleTests(TestCase):
    setUp = test_apple_app_store.AppleSubscriptionEvidenceTests.setUp
    evidence = test_apple_app_store.AppleSubscriptionEvidenceTests.evidence
    def test_old_basic_transaction_cannot_replace_an_immediate_upgrade(self):
        now = timezone.now()
        basic_product = BillingProduct.objects.create(
            provider=PaymentProvider.APPLE_APP_STORE,
            environment="sandbox", external_product_id="com.myscoope.basic.monthly",
            account_plan=self.basic, amount_minor=0,
        )
        newer = self.evidence(transaction_id="202", purchase_date=now, signed_date=now)
        sync_apple_transaction(newer, source="mobile_storekit")
        old = self.evidence(
            transaction_id="201", product_id=basic_product.external_product_id,
            purchase_date=now - timedelta(days=1), signed_date=now + timedelta(seconds=1),
        )
        sync_apple_transaction(old, source="mobile_storekit")
        self.assertEqual(AccountSubscription.objects.get(user=self.user).plan, self.pro)

    def test_a_cached_storekit_transaction_cannot_undo_a_refund(self):
        now = timezone.now()
        original = self.evidence(signed_date=now)
        sync_apple_transaction(original, source="mobile_storekit")
        sync_apple_transaction(
            self.evidence(signed_date=now + timedelta(seconds=1), revocation_date=now),
            source="app_store_notification_v2",
        )
        sync_apple_transaction(original, source="mobile_storekit")
        self.assertEqual(AccountSubscription.objects.get(user=self.user).status, AccountSubscription.Status.CANCELED)

    def test_grace_period_keeps_access_until_its_verified_deadline(self):
        now = timezone.now()
        provider = sync_apple_transaction(self.evidence(
            status="grace_period", expires_date=now - timedelta(hours=1),
            metadata={"apple_grace_period_expires_date": int((now + timedelta(days=3)).timestamp() * 1000)},
        ), source="app_store_notification_v2")
        self.assertEqual(provider.status, ProviderSubscription.Status.AUTHORIZED)
        self.assertGreater(provider.current_period_end, now)

    def test_stored_expired_authorization_cannot_hide_an_active_other_provider(self):
        expired = sync_apple_transaction(self.evidence(), source="mobile_storekit")
        expired.current_period_end = timezone.now() - timedelta(seconds=1)
        expired.save(update_fields=["current_period_end"])
        from billing.application.services.projections import project_provider_subscription
        product = BillingProduct.objects.create(
            provider=PaymentProvider.MERCADO_PAGO, external_product_id="live-basic",
            account_plan=self.basic, amount_minor=0,
        )
        other = ProviderSubscription.objects.create(
            provider=PaymentProvider.MERCADO_PAGO, external_subscription_id="active-basic",
            user=self.user, product=product, status="authorized",
        )
        project_provider_subscription(other)
        self.assertEqual(AccountSubscription.objects.get(user=self.user).plan, self.basic)

    def test_a_subscription_without_expiration_cannot_grant_perpetual_access(self):
        with self.assertRaises(AppleEvidenceError):
            sync_apple_transaction(self.evidence(expires_date=None), source="mobile_storekit")
        self.assertFalse(ProviderSubscription.objects.exists())

    def test_cancellation_preserves_access_until_period_end(self):
        provider = sync_apple_transaction(self.evidence(metadata={"apple_auto_renew_enabled": False}), source="app_store_notification_v2")
        self.assertTrue(provider.cancel_at_period_end)
        self.assertEqual(AccountSubscription.objects.get(user=self.user).status, "active")

    def test_transaction_without_renewal_info_cannot_erase_a_verified_cancellation(self):
        now = timezone.now()
        sync_apple_transaction(self.evidence(purchase_date=now, signed_date=now,
            metadata={"apple_auto_renew_enabled": False}), source="app_store_notification_v2")
        provider = sync_apple_transaction(self.evidence(transaction_id="new-receipt",
            purchase_date=now + timedelta(seconds=1), signed_date=now + timedelta(seconds=1)), source="mobile_storekit")
        self.assertTrue(provider.cancel_at_period_end)
        provider = sync_apple_transaction(self.evidence(transaction_id="new-receipt",
            purchase_date=now + timedelta(seconds=1), signed_date=now + timedelta(seconds=2),
            metadata={"apple_auto_renew_enabled": True}), source="app_store_server_api")
        self.assertFalse(provider.cancel_at_period_end)

    def test_a_scheduled_downgrade_does_not_switch_current_benefits(self):
        sync_apple_transaction(self.evidence(metadata={"apple_next_product_id": "basic.annual"}), source="app_store_notification_v2")
        self.assertEqual(AccountSubscription.objects.get(user=self.user).plan, self.pro)

    def test_a_new_renewal_after_retry_restores_access(self):
        now = timezone.now()
        sync_apple_transaction(self.evidence(status="billing_retry", signed_date=now), source="app_store_notification_v2")
        self.assertEqual(AccountSubscription.objects.get(user=self.user).status, "past_due")
        sync_apple_transaction(self.evidence(transaction_id="renewal", purchase_date=now, signed_date=now), source="app_store_server_api")
        self.assertEqual(AccountSubscription.objects.get(user=self.user).status, "active")

    def test_refund_reversal_requires_newer_authoritative_evidence(self):
        now = timezone.now()
        sync_apple_transaction(self.evidence(revocation_date=now, signed_date=now), source="app_store_notification_v2")
        sync_apple_transaction(self.evidence(signed_date=now + timedelta(seconds=1)), source="app_store_server_api")
        self.assertEqual(AccountSubscription.objects.get(user=self.user).status, "active")

    def test_expired_grace_removes_access(self):
        provider = sync_apple_transaction(self.evidence(
            status="grace_period", expires_date=timezone.now() - timedelta(days=2),
            metadata={"apple_grace_period_expires_date": int((timezone.now() - timedelta(seconds=1)).timestamp() * 1000)},
        ), source="app_store_server_api")
        self.assertEqual(provider.status, "expired")

    def test_a_renewal_after_deletion_keeps_financial_evidence_without_recreating_entitlements(self):
        from accounts.services.deletion import delete_user_account
        sync_apple_transaction(self.evidence(), source="app_store_notification_v2")
        delete_user_account(user=self.user, source="test_late_apple_renewal")
        sync_apple_transaction(self.evidence(transaction_id="renewal-after-deletion", purchase_date=timezone.now()),
            source="app_store_server_api")
        self.assertFalse(AccountSubscription.objects.filter(user=self.user).exists())
        self.assertEqual(ProviderSubscription.objects.get(user=self.user).metadata["apple_latest_transaction_id"], "renewal-after-deletion")
