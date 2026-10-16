from __future__ import annotations

import base64
import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import jwt
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import CreditLedger, CreditWallet
from accounts.seed_plans import seed_account_plans
from billing.application.contracts import GooglePlayProductEvidence, GooglePlaySubscriptionEvidence
from billing.application.services.catalog import GooglePlayCatalogReference, configure_google_play_catalog
from billing.application.services.credit_packs import configure_credit_pack_product, settle_google_play_credit_pack
from billing.application.services.google_play import (
    GooglePlayEvidenceError,
    get_or_create_google_play_account_token,
    sync_google_play_subscription,
)
from billing.catalog import seed_billing_offers, seed_credit_pack_offers
from billing.infrastructure.providers.google_play_pubsub import (
    GooglePubSubConfigurationError,
    InvalidGooglePubSubPush,
    decode_google_play_notification,
    verify_google_pubsub_authorization,
)
from billing.models import BillingEvent, CreditPackPurchase, PaymentProvider, ProviderSubscription


def _envelope(payload: dict, *, message_id: str = "message-1") -> dict:
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return {
        "message": {
            "messageId": message_id,
            "publishTime": "2026-10-05T20:00:00Z",
            "data": encoded,
        },
        "subscription": "projects/example/subscriptions/myscoope-rtdn",
    }


class GooglePubSubPushTests(SimpleTestCase):
    def test_decoder_normalizes_subscription_without_exposing_envelope_details(self):
        notification = decode_google_play_notification(_envelope({
            "version": "1.0",
            "packageName": "com.myscoope.app",
            "eventTimeMillis": "1791230400000",
            "subscriptionNotification": {
                "version": "1.0",
                "notificationType": 2,
                "purchaseToken": "purchase-token",
                "subscriptionId": "myscoope_basic",
            },
        }))

        self.assertEqual(notification.kind, "subscription")
        self.assertEqual(notification.product_id, "myscoope_basic")
        self.assertEqual(notification.purchase_token, "purchase-token")

    def test_voided_purchase_requires_order_and_product_type(self):
        payload = {
            "packageName": "com.myscoope.app",
            "voidedPurchaseNotification": {
                "purchaseToken": "purchase-token", "orderId": "GPA.123", "productType": 2,
            },
        }
        notification = decode_google_play_notification(_envelope(payload))
        self.assertEqual((notification.kind, notification.order_id, notification.product_type),
                         ("voided_purchase", "GPA.123", 2))
        payload["voidedPurchaseNotification"]["productType"] = 3
        with self.assertRaises(InvalidGooglePubSubPush):
            decode_google_play_notification(_envelope(payload))

    def test_authorization_requires_expected_verified_service_account(self):
        client = Mock()
        client.get_signing_key_from_jwt.return_value = SimpleNamespace(key="verification-key")
        claims = {
            "aud": "https://example.test/billing/webhooks/google-play/",
            "email": "pubsub@example.iam.gserviceaccount.com",
            "email_verified": True,
            "exp": 2_000_000_000,
            "iat": 1_999_999_000,
            "iss": "https://accounts.google.com",
        }
        with patch("billing.infrastructure.providers.google_play_pubsub.jwt.decode", return_value=claims) as decode:
            result = verify_google_pubsub_authorization(
                "Bearer signed-token",
                audience=claims["aud"],
                service_account_email=claims["email"],
                jwk_client=client,
            )

        self.assertEqual(result, claims)
        decode.assert_called_once()
        with patch("billing.infrastructure.providers.google_play_pubsub.jwt.decode", return_value=claims):
            with self.assertRaises(InvalidGooglePubSubPush):
                verify_google_pubsub_authorization(
                    "Bearer signed-token",
                    audience=claims["aud"],
                    service_account_email="other@example.iam.gserviceaccount.com",
                    jwk_client=client,
                )

    def test_signing_key_outage_is_retryable_configuration_failure(self):
        client = Mock()
        client.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientConnectionError("unavailable")

        with self.assertRaises(GooglePubSubConfigurationError):
            verify_google_pubsub_authorization(
                "Bearer signed-token",
                audience="https://example.test/billing/webhooks/google-play/",
                service_account_email="pubsub@example.iam.gserviceaccount.com",
                jwk_client=client,
            )


@override_settings(
    BILLING_GOOGLE_PLAY_RTDN_ENABLED=True,
    BILLING_GOOGLE_PLAY_ENVIRONMENT="sandbox",
    BILLING_GOOGLE_PLAY_PACKAGE_NAME="com.myscoope.app",
    BILLING_GOOGLE_PLAY_PUBSUB_AUDIENCE="https://example.test/billing/webhooks/google-play/",
    BILLING_GOOGLE_PLAY_PUBSUB_SERVICE_ACCOUNT_EMAIL="pubsub@example.iam.gserviceaccount.com",
)
class GooglePlayRTDNTests(TestCase):
    def setUp(self):
        seed_account_plans()
        seed_billing_offers()
        seed_credit_pack_offers()
        self.user = get_user_model().objects.create_user(username="play-rtdn")
        self.account_token = get_or_create_google_play_account_token(self.user)
        self.url = reverse("billing:google_play_webhook")

    def _post(self, payload: dict, *, message_id: str = "message-1"):
        return self.client.post(
            self.url,
            data=json.dumps(_envelope(payload, message_id=message_id)),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer signed-token",
        )

    def _subscription_payload(self, *, token="subscription-token"):
        return {
            "version": "1.0",
            "packageName": "com.myscoope.app",
            "eventTimeMillis": "1791230400000",
            "subscriptionNotification": {
                "version": "1.0",
                "notificationType": 2,
                "purchaseToken": token,
                "subscriptionId": "myscoope_basic",
            },
        }

    def test_disabled_endpoint_is_hidden_before_authentication(self):
        with override_settings(BILLING_GOOGLE_PLAY_RTDN_ENABLED=False):
            response = self._post(self._subscription_payload())
        self.assertEqual(response.status_code, 404)
        self.assertFalse(BillingEvent.objects.exists())

    def test_invalid_push_authentication_is_rejected_before_persistence(self):
        with patch(
            "billing.interface.views.verify_google_pubsub_authorization",
            side_effect=InvalidGooglePubSubPush("invalid"),
        ):
            response = self._post(self._subscription_payload())
        self.assertEqual(response.status_code, 401)
        self.assertFalse(BillingEvent.objects.exists())

    def test_subscription_rtdn_selects_sandbox_catalog_and_is_idempotent(self):
        references = tuple(
            GooglePlayCatalogReference(
                offer_code=f"{plan}-{cadence}",
                product_id=f"myscoope_{plan}",
                base_plan_id=cadence,
            )
            for plan in ("basic", "pro")
            for cadence in ("monthly", "annual")
        )
        configure_google_play_catalog(environment="sandbox", references=references)
        configure_google_play_catalog(environment="live", references=references)
        evidence = GooglePlaySubscriptionEvidence(
            purchase_token="subscription-token",
            product_id="myscoope_basic",
            base_plan_id="monthly",
            status="SUBSCRIPTION_STATE_ACTIVE",
            environment="sandbox",
            expiry_time=(timezone.now() + timedelta(days=30)).isoformat(),
            obfuscated_account_id=self.account_token.token,
            acknowledged=True,
            auto_renewing=True,
        )
        gateway = SimpleNamespace(verify_subscription=Mock(return_value=evidence))
        with (
            patch("billing.interface.views.verify_google_pubsub_authorization"),
            patch("billing.interface.views.build_google_play_gateway", return_value=gateway),
        ):
            first = self._post(self._subscription_payload())
            duplicate = self._post(self._subscription_payload())

        self.assertEqual((first.status_code, duplicate.status_code), (200, 200))
        gateway.verify_subscription.assert_called_once_with("subscription-token")
        subscription = ProviderSubscription.objects.get(external_subscription_id="subscription-token")
        self.assertEqual(subscription.product.environment, "sandbox")
        self.assertEqual(BillingEvent.objects.count(), 1)
        event = BillingEvent.objects.get()
        self.assertEqual(event.status, BillingEvent.Status.PROCESSED)
        self.assertNotIn("subscription-token", json.dumps(event.payload))
        self.assertNotIn("subscription-token", event.resource_id)

    def test_cross_environment_subscription_fails_closed_and_is_operable(self):
        evidence = GooglePlaySubscriptionEvidence(
            purchase_token="subscription-token",
            product_id="myscoope_basic",
            base_plan_id="monthly",
            status="SUBSCRIPTION_STATE_ACTIVE",
            environment="live",
            obfuscated_account_id=self.account_token.token,
        )
        gateway = SimpleNamespace(verify_subscription=Mock(return_value=evidence))
        with (
            patch("billing.interface.views.verify_google_pubsub_authorization"),
            patch("billing.interface.views.build_google_play_gateway", return_value=gateway),
        ):
            response = self._post(self._subscription_payload())

        self.assertEqual(response.status_code, 502)
        event = BillingEvent.objects.get()
        self.assertEqual(event.status, BillingEvent.Status.FAILED)
        self.assertEqual(event.last_error, "GooglePlayEvidenceError")
        self.assertFalse(ProviderSubscription.objects.exists())

    def test_existing_purchase_token_cannot_be_transferred_to_another_user(self):
        references = (
            GooglePlayCatalogReference(
                offer_code="basic-monthly",
                product_id="myscoope_basic",
                base_plan_id="monthly",
            ),
        )
        configure_google_play_catalog(environment="sandbox", references=references)
        original = GooglePlaySubscriptionEvidence(
            purchase_token="owned-subscription-token",
            product_id="myscoope_basic",
            base_plan_id="monthly",
            status="SUBSCRIPTION_STATE_ACTIVE",
            environment="sandbox",
            expiry_time=(timezone.now() + timedelta(days=30)).isoformat(),
            obfuscated_account_id=self.account_token.token,
        )
        sync_google_play_subscription(
            original,
            expected_user=self.user,
            expected_environment="sandbox",
        )
        other_user = get_user_model().objects.create_user(username="play-rtdn-other")
        other_token = get_or_create_google_play_account_token(other_user)
        replay = GooglePlaySubscriptionEvidence(
            **{
                **original.__dict__,
                "obfuscated_account_id": other_token.token,
            },
        )

        with self.assertRaises(GooglePlayEvidenceError):
            sync_google_play_subscription(
                replay,
                expected_user=other_user,
                expected_environment="sandbox",
            )

        subscription = ProviderSubscription.objects.get(
            external_subscription_id=original.purchase_token,
        )
        self.assertEqual(subscription.user, self.user)

    def test_replacement_retires_linked_token_and_old_notification_cannot_restore_it(self):
        configure_google_play_catalog(environment="sandbox", references=(
            GooglePlayCatalogReference("basic-monthly", "myscoope_basic", "monthly"),
            GooglePlayCatalogReference("pro-monthly", "myscoope_pro", "monthly"),
        ))
        old = GooglePlaySubscriptionEvidence(
            purchase_token="old-basic-token", product_id="myscoope_basic", base_plan_id="monthly",
            status="SUBSCRIPTION_STATE_ACTIVE", environment="sandbox",
            expiry_time=(timezone.now() + timedelta(days=30)).isoformat(),
            obfuscated_account_id=self.account_token.token,
        )
        sync_google_play_subscription(old, expected_user=self.user, expected_environment="sandbox")
        new = GooglePlaySubscriptionEvidence(
            purchase_token="new-pro-token", product_id="myscoope_pro", base_plan_id="monthly",
            status="SUBSCRIPTION_STATE_ACTIVE", environment="sandbox",
            expiry_time=(timezone.now() + timedelta(days=30)).isoformat(),
            obfuscated_account_id=self.account_token.token,
            metadata={"linkedPurchaseToken": old.purchase_token},
        )
        sync_google_play_subscription(new, expected_user=self.user, expected_environment="sandbox")
        sync_google_play_subscription(old, expected_user=self.user, expected_environment="sandbox")
        sync_google_play_subscription(old, expected_user=self.user, expected_environment="sandbox")

        self.assertEqual(ProviderSubscription.objects.get(external_subscription_id=old.purchase_token).status,
                         ProviderSubscription.Status.EXPIRED)
        self.assertEqual(ProviderSubscription.objects.get(external_subscription_id=new.purchase_token).status,
                         ProviderSubscription.Status.AUTHORIZED)

    def test_replacement_cannot_retire_another_users_purchase(self):
        configure_google_play_catalog(environment="sandbox", references=(
            GooglePlayCatalogReference("basic-monthly", "myscoope_basic", "monthly"),
            GooglePlayCatalogReference("pro-monthly", "myscoope_pro", "monthly"),
        ))
        old = GooglePlaySubscriptionEvidence(
            purchase_token="other-basic-token", product_id="myscoope_basic", base_plan_id="monthly",
            status="SUBSCRIPTION_STATE_ACTIVE", environment="sandbox",
            expiry_time=(timezone.now() + timedelta(days=30)).isoformat(),
            obfuscated_account_id=self.account_token.token,
        )
        sync_google_play_subscription(old, expected_user=self.user, expected_environment="sandbox")
        other = get_user_model().objects.create_user(username="play-replacement-other")
        other_token = get_or_create_google_play_account_token(other)
        new = GooglePlaySubscriptionEvidence(
            purchase_token="other-pro-token", product_id="myscoope_pro", base_plan_id="monthly",
            status="SUBSCRIPTION_STATE_ACTIVE", environment="sandbox",
            obfuscated_account_id=other_token.token,
            metadata={"linkedPurchaseToken": old.purchase_token},
        )
        with self.assertRaises(GooglePlayEvidenceError):
            sync_google_play_subscription(new, expected_user=other, expected_environment="sandbox")
        self.assertEqual(ProviderSubscription.objects.get().status, ProviderSubscription.Status.AUTHORIZED)

    def test_long_google_purchase_token_is_stored_for_lifecycle_reconciliation(self):
        configure_google_play_catalog(environment="sandbox", references=(
            GooglePlayCatalogReference("basic-monthly", "myscoope_basic", "monthly"),
        ))
        token = "g" * 512
        evidence = GooglePlaySubscriptionEvidence(
            purchase_token=token, product_id="myscoope_basic", base_plan_id="monthly",
            status="SUBSCRIPTION_STATE_ACTIVE", environment="sandbox",
            expiry_time=(timezone.now() + timedelta(days=30)).isoformat(),
            obfuscated_account_id=self.account_token.token,
        )
        sync_google_play_subscription(evidence, expected_user=self.user, expected_environment="sandbox")
        self.assertEqual(ProviderSubscription.objects.get().external_subscription_id, token)

    def test_one_time_product_rtdn_grants_once_after_server_verification(self):
        configure_credit_pack_product(
            provider=PaymentProvider.GOOGLE_PLAY,
            environment="sandbox",
            offer_code="credits-500",
            external_product_id="myscoope.credits.500",
        )
        evidence = GooglePlayProductEvidence(
            purchase_token="product-token",
            product_id="myscoope.credits.500",
            status="PURCHASED",
            obfuscated_account_id=self.account_token.token,
            order_id="GPA.123",
            environment="sandbox",
        )
        gateway = SimpleNamespace(verify_product=Mock(return_value=evidence))
        payload = {
            "version": "1.0",
            "packageName": "com.myscoope.app",
            "eventTimeMillis": "1791230400000",
            "oneTimeProductNotification": {
                "version": "1.0",
                "notificationType": 1,
                "purchaseToken": "product-token",
                "sku": "myscoope.credits.500",
            },
        }
        with (
            patch("billing.interface.views.verify_google_pubsub_authorization"),
            patch("billing.interface.views.build_google_play_gateway", return_value=gateway),
        ):
            first = self._post(payload, message_id="product-message")
            duplicate = self._post(payload, message_id="product-message")

        self.assertEqual((first.status_code, duplicate.status_code), (200, 200))
        gateway.verify_product.assert_called_once_with("product-token")
        self.assertEqual(CreditPackPurchase.objects.count(), 1)
        self.assertEqual(CreditPackPurchase.objects.get().credits_granted, 500)

    def test_voided_credit_pack_reverses_once_after_full_server_verification(self):
        configure_credit_pack_product(
            provider=PaymentProvider.GOOGLE_PLAY,
            environment="sandbox",
            offer_code="credits-500",
            external_product_id="myscoope.credits.500",
        )
        settled = GooglePlayProductEvidence(
            purchase_token="voided-product-token", product_id="myscoope.credits.500",
            status="PURCHASED", obfuscated_account_id=self.account_token.token,
            order_id="GPA.voided", environment="sandbox",
        )
        settle_google_play_credit_pack(user=self.user, evidence=settled)
        self.assertEqual(CreditWallet.objects.get(user=self.user).purchased_balance, 500)
        verified = GooglePlayProductEvidence(
            **{**settled.__dict__, "status": "CANCELLED", "metadata": {"productLineItem": [{
                "productId": settled.product_id,
                "productOfferDetails": {"quantity": 1, "refundableQuantity": 0},
            }]}}
        )
        gateway = SimpleNamespace(verify_product=Mock(return_value=verified))
        payload = {
            "packageName": "com.myscoope.app",
            "voidedPurchaseNotification": {
                "purchaseToken": settled.purchase_token, "orderId": settled.order_id,
                "productType": 2, "refundType": 1,
            },
        }
        with (
            patch("billing.interface.views.verify_google_pubsub_authorization"),
            patch("billing.interface.views.build_google_play_gateway", return_value=gateway),
        ):
            first = self._post(payload, message_id="voided-product-1")
            repeated = self._post(payload, message_id="voided-product-2")

        self.assertEqual((first.status_code, repeated.status_code), (200, 200))
        self.assertEqual(CreditPackPurchase.objects.get().status, CreditPackPurchase.Status.REFUNDED)
        self.assertEqual(CreditWallet.objects.get(user=self.user).purchased_balance, 0)
        self.assertEqual(CreditLedger.objects.filter(user=self.user, reference_type="credit_pack_refund").count(), 1)

    def test_voided_credit_pack_with_unmatched_order_keeps_credits(self):
        configure_credit_pack_product(
            provider=PaymentProvider.GOOGLE_PLAY, environment="sandbox",
            offer_code="credits-500", external_product_id="myscoope.credits.500",
        )
        settled = GooglePlayProductEvidence(
            purchase_token="mismatched-product-token", product_id="myscoope.credits.500",
            status="PURCHASED", obfuscated_account_id=self.account_token.token,
            order_id="GPA.original", environment="sandbox",
        )
        settle_google_play_credit_pack(user=self.user, evidence=settled)
        gateway = SimpleNamespace(verify_product=Mock(return_value=GooglePlayProductEvidence(
            **{**settled.__dict__, "status": "CANCELLED", "order_id": "GPA.other",
               "metadata": {"productLineItem": [{"productOfferDetails": {"quantity": 1, "refundableQuantity": 0}}]}},
        )))
        payload = {
            "packageName": "com.myscoope.app",
            "voidedPurchaseNotification": {
                "purchaseToken": settled.purchase_token, "orderId": "GPA.other",
                "productType": 2, "refundType": 1,
            },
        }
        with (
            patch("billing.interface.views.verify_google_pubsub_authorization"),
            patch("billing.interface.views.build_google_play_gateway", return_value=gateway),
        ):
            response = self._post(payload, message_id="voided-mismatch")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(CreditWallet.objects.get(user=self.user).purchased_balance, 500)
        self.assertEqual(BillingEvent.objects.get().status, BillingEvent.Status.FAILED)

    def test_voided_subscription_refreshes_subscription_state(self):
        configure_google_play_catalog(environment="sandbox", references=(
            GooglePlayCatalogReference(
                offer_code="basic-monthly", product_id="myscoope_basic", base_plan_id="monthly",
            ),
        ))
        active = GooglePlaySubscriptionEvidence(
            purchase_token="voided-subscription-token", product_id="myscoope_basic",
            base_plan_id="monthly", status="SUBSCRIPTION_STATE_ACTIVE",
            environment="sandbox", expiry_time=(timezone.now() + timedelta(days=30)).isoformat(),
            obfuscated_account_id=self.account_token.token,
        )
        sync_google_play_subscription(active, expected_user=self.user, expected_environment="sandbox")
        expired = GooglePlaySubscriptionEvidence(**{
            **active.__dict__, "status": "SUBSCRIPTION_STATE_EXPIRED",
            "expiry_time": (timezone.now() - timedelta(days=1)).isoformat(),
        })
        gateway = SimpleNamespace(verify_subscription=Mock(return_value=expired), verify_product=Mock())
        payload = {
            "packageName": "com.myscoope.app",
            "voidedPurchaseNotification": {
                "purchaseToken": active.purchase_token, "orderId": "GPA.subscription.0",
                "productType": 1, "refundType": 1,
            },
        }
        with (
            patch("billing.interface.views.verify_google_pubsub_authorization"),
            patch("billing.interface.views.build_google_play_gateway", return_value=gateway),
        ):
            response = self._post(payload, message_id="voided-subscription")
        self.assertEqual(response.status_code, 200)
        gateway.verify_subscription.assert_called_once_with(active.purchase_token)
        gateway.verify_product.assert_not_called()
        self.assertEqual(ProviderSubscription.objects.get().status, ProviderSubscription.Status.EXPIRED)
