import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription
from billing.application.contracts import AppleNotificationEvidence, AppleTransactionEvidence
from billing.application.services.apple_app_store import (
    UnknownAppleAccountToken,
    UnsupportedAppleOwnership,
    get_or_create_apple_app_account_token,
    sync_apple_transaction,
)
from billing.application.services.projections import project_provider_subscription
from billing.infrastructure.providers.apple_app_store import AppleAppStoreClient, InvalidAppleSignedData
from billing.models import BillingEvent, BillingProduct, PaymentProvider, ProviderSubscription


class AppleSignedDataAdapterTests(SimpleTestCase):
    def test_bundled_apple_root_certificate_builds_a_fail_closed_verifier(self):
        certificate = Path(__file__).resolve().parents[1] / "infrastructure" / "providers" / "AppleRootCA-G3.cer"
        gateway = AppleAppStoreClient(
            bundle_id="com.myscoope.app",
            environment="sandbox",
            root_certificate_paths=(str(certificate),),
            online_checks=False,
        )

        with self.assertRaises(InvalidAppleSignedData):
            gateway.verify_transaction("invalid.invalid.invalid")


class AppleSubscriptionEvidenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="apple-user")
        self.other = User.objects.create_user(username="apple-other")
        self.basic = AccountPlan.objects.create(
            slug="apple-basic", name="Apple Basic", status=AccountPlan.Status.ACTIVE, display_order=10
        )
        self.pro = AccountPlan.objects.create(
            slug="apple-pro", name="Apple Pro", status=AccountPlan.Status.ACTIVE, display_order=20
        )
        self.apple_product = BillingProduct.objects.create(
            provider=PaymentProvider.APPLE_APP_STORE,
            external_product_id="com.myscoope.pro.monthly",
            account_plan=self.pro,
            amount_minor=0,
        )
        self.token = get_or_create_apple_app_account_token(self.user)

    def evidence(self, **overrides):
        now = timezone.now()
        values = {
            "original_transaction_id": "original-100",
            "transaction_id": "transaction-101",
            "product_id": self.apple_product.external_product_id,
            "app_account_token": str(self.token.token),
            "status": "active",
            "purchase_date": int((now - timedelta(days=1)).timestamp() * 1000),
            "expires_date": int((now + timedelta(days=29)).timestamp() * 1000),
            "environment": "Sandbox",
            "ownership_type": "PURCHASED",
        }
        values.update(overrides)
        return AppleTransactionEvidence(**values)

    def test_verified_transaction_projects_one_effective_account_subscription(self):
        provider = sync_apple_transaction(self.evidence(), expected_user=self.user, source="mobile_storekit")

        account = AccountSubscription.objects.get(user=self.user)
        self.assertEqual(provider.status, ProviderSubscription.Status.AUTHORIZED)
        self.assertEqual(account.plan, self.pro)
        self.assertEqual(account.source, AccountSubscription.Source.BILLING)
        self.assertEqual(account.metadata["billing_provider"], PaymentProvider.APPLE_APP_STORE)

    def test_cross_account_replay_and_family_sharing_are_rejected(self):
        with self.assertRaises(UnknownAppleAccountToken):
            sync_apple_transaction(self.evidence(), expected_user=self.other, source="mobile_storekit")
        with self.assertRaises(UnsupportedAppleOwnership):
            sync_apple_transaction(self.evidence(ownership_type="FAMILY_SHARED"), source="notification")

    def test_revocation_removes_access_without_deleting_evidence(self):
        provider = sync_apple_transaction(self.evidence(), source="mobile_storekit")
        provider = sync_apple_transaction(
            self.evidence(status="revoked", revocation_date=int(timezone.now().timestamp() * 1000)),
            source="notification",
        )

        self.assertEqual(provider.status, ProviderSubscription.Status.CANCELED)
        self.assertEqual(AccountSubscription.objects.get(user=self.user).status, AccountSubscription.Status.CANCELED)
        self.assertTrue(ProviderSubscription.objects.filter(pk=provider.pk).exists())

    def test_dual_active_channels_are_deterministic_and_reported(self):
        mp_product = BillingProduct.objects.create(
            provider=PaymentProvider.MERCADO_PAGO,
            external_product_id="mp-basic",
            account_plan=self.basic,
            amount_minor=1000,
        )
        mp = ProviderSubscription.objects.create(
            user=self.user,
            product=mp_product,
            provider=PaymentProvider.MERCADO_PAGO,
            external_subscription_id="mp-active",
            status=ProviderSubscription.Status.AUTHORIZED,
        )
        project_provider_subscription(mp)
        sync_apple_transaction(self.evidence(), source="mobile_storekit")

        account = AccountSubscription.objects.get(user=self.user)
        self.assertEqual(account.plan, self.pro)
        self.assertEqual(account.metadata["billing_active_providers"], ["apple_app_store", "mercado_pago"])
        self.assertTrue(account.metadata["billing_duplicate_active_providers"])


class _AppleGateway:
    def __init__(self, notification=None, error=None):
        self.notification = notification
        self.error = error

    def verify_notification(self, signed_payload):
        if self.error:
            raise self.error
        return self.notification


@override_settings(BILLING_APPLE_NOTIFICATIONS_ENABLED=True)
class AppleNotificationWebhookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="apple-hook")
        self.plan = AccountPlan.objects.create(slug="hook-plan", name="Hook", status=AccountPlan.Status.ACTIVE)
        self.product = BillingProduct.objects.create(
            provider=PaymentProvider.APPLE_APP_STORE,
            external_product_id="com.myscoope.hook",
            account_plan=self.plan,
            amount_minor=0,
        )
        token = get_or_create_apple_app_account_token(self.user)
        transaction = AppleTransactionEvidence(
            original_transaction_id="hook-original",
            transaction_id="hook-transaction",
            product_id=self.product.external_product_id,
            app_account_token=str(token.token),
            expires_date=int((timezone.now() + timedelta(days=30)).timestamp() * 1000),
            ownership_type="PURCHASED",
        )
        self.notification = AppleNotificationEvidence(
            notification_uuid="notification-uuid",
            notification_type="DID_RENEW",
            environment="Sandbox",
            transaction=transaction,
        )
        self.url = reverse("billing:apple_app_store_webhook")

    def test_invalid_signed_payload_is_rejected_before_inbox(self):
        gateway = _AppleGateway(error=InvalidAppleSignedData("invalid"))
        with patch("billing.interface.views.build_apple_app_store_gateway", return_value=gateway):
            response = self.client.post(
                self.url,
                data=json.dumps({"signedPayload": "not-a-jws"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(BillingEvent.objects.exists())

    def test_verified_notification_is_idempotent_and_does_not_store_jws(self):
        gateway = _AppleGateway(notification=self.notification)
        body = json.dumps({"signedPayload": "header.payload.signature"})
        with patch("billing.interface.views.build_apple_app_store_gateway", return_value=gateway):
            first = self.client.post(self.url, data=body, content_type="application/json")
            duplicate = self.client.post(self.url, data=body, content_type="application/json")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(duplicate.status_code, 200)
        event = BillingEvent.objects.get()
        self.assertEqual(event.status, BillingEvent.Status.PROCESSED)
        self.assertNotIn("signedPayload", event.payload)
        self.assertEqual(ProviderSubscription.objects.count(), 1)
