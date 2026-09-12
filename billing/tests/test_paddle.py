from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from accounts.models import AccountPlan, AccountSubscription
from billing.application.services.paddle_checkout import (
    PaddleCheckoutUnavailable,
    build_paddle_checkout_payload,
)
from billing.infrastructure.providers.paddle import (
    PaddleClient,
    PaddlePortalLinks,
    PaddleProviderError,
)
from billing.infrastructure.providers.paddle_webhooks import (
    InvalidPaddleSignature,
    verify_paddle_signature,
)
from billing.models import (
    BillingEvent,
    BillingOffer,
    BillingPayment,
    BillingProduct,
    PaymentProvider,
    ProviderSubscription,
    TaxDocument,
)

User = get_user_model()
PADDLE_SECRET = "pdl_ntfset_test_secret"


class PaddleSignatureTests(SimpleTestCase):
    def test_valid_signature_uses_the_untouched_raw_body(self):
        body = b'{"event_id":"evt_1"}'
        timestamp = 1_750_000_000
        signature = _signature(body, timestamp=timestamp)

        verify_paddle_signature(
            raw_body=body,
            signature_header=signature,
            secret=PADDLE_SECRET,
            tolerance_seconds=5,
            current_time=timestamp,
        )

    def test_tampered_or_stale_signatures_are_rejected(self):
        body = b'{"event_id":"evt_1"}'
        timestamp = 1_750_000_000

        with self.assertRaises(InvalidPaddleSignature):
            verify_paddle_signature(
                raw_body=body + b" ",
                signature_header=_signature(body, timestamp=timestamp),
                secret=PADDLE_SECRET,
                tolerance_seconds=5,
                current_time=timestamp,
            )

        with self.assertRaises(InvalidPaddleSignature):
            verify_paddle_signature(
                raw_body=body,
                signature_header=_signature(body, timestamp=timestamp),
                secret=PADDLE_SECRET,
                tolerance_seconds=5,
                current_time=timestamp + 6,
            )

    def test_customer_portal_client_uses_api_key_without_exposing_it_in_errors(self):
        session = _FakeSession(_FakeResponse({
            "data": {
                "urls": {
                    "general": {"overview": "https://customer-portal.paddle.com/session?token=ok"},
                    "subscriptions": [{
                        "id": "sub_test",
                        "cancel_subscription": "https://customer-portal.paddle.com/session?action=cancel",
                        "update_subscription_payment_method": "https://customer-portal.paddle.com/session?action=payment",
                    }],
                },
            },
        }))
        client = PaddleClient(
            api_key="pdl_sdbx_apikey_secret",
            base_url="https://sandbox-api.paddle.com",
            session=session,
        )

        links = client.create_customer_portal_session(customer_id="ctm_test", subscription_id="sub_test")

        self.assertIn("action=cancel", links.cancel_subscription)
        self.assertEqual(session.calls[0][1], "https://sandbox-api.paddle.com/customers/ctm_test/portal-sessions")
        self.assertEqual(session.calls[0][2]["json"], {"subscription_ids": ["sub_test"]})

        failing = PaddleClient(
            api_key="pdl_sdbx_apikey_secret",
            base_url="https://sandbox-api.paddle.com",
            session=_FakeSession(_FakeResponse({"secret": "response-body"}, status_code=500)),
        )
        with self.assertRaises(PaddleProviderError) as raised:
            failing.create_customer_portal_session(customer_id="ctm_test", subscription_id="sub_test")
        self.assertNotIn("pdl_sdbx_apikey_secret", str(raised.exception))
        self.assertNotIn("response-body", str(raised.exception))

        with self.assertRaises(PaddleProviderError):
            client.create_customer_portal_session(
                customer_id="ctm_test/portal-sessions",
                subscription_id="sub_test",
            )


@override_settings(
    BILLING_PADDLE_ENVIRONMENT="sandbox",
    BILLING_PADDLE_CHECKOUT_ENABLED=True,
    BILLING_PADDLE_WEBHOOK_ENABLED=True,
    BILLING_PADDLE_CLIENT_TOKEN="test_client_token",
    BILLING_PADDLE_WEBHOOK_SECRET=PADDLE_SECRET,
    BILLING_PADDLE_WEBHOOK_TOLERANCE_SECONDS=30,
    BILLING_PUBLIC_BASE_URL="https://staging.myscoope.com",
)
class PaddleSandboxIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="paddle-user",
            email="paddle-user@example.com",
            password="test-pass",
        )
        self.plan = AccountPlan.objects.create(
            slug="paddle-basic",
            name="Paddle Basic",
            status=AccountPlan.Status.ACTIVE,
        )
        self.offer = BillingOffer.objects.create(
            code="paddle-basic-monthly",
            account_plan=self.plan,
            amount_minor=7_990,
            currency="CLP",
            interval=BillingOffer.Interval.MONTH,
        )
        self.product = BillingProduct.objects.create(
            provider=PaymentProvider.PADDLE,
            environment=BillingProduct.Environment.SANDBOX,
            external_product_id="pro_sandbox_basic",
            external_price_id="pri_sandbox_basic_monthly",
            offer=self.offer,
            account_plan=self.plan,
            amount_minor=7_990,
            currency="CLP",
            interval=BillingProduct.Interval.MONTH,
        )
        self.checkout = build_paddle_checkout_payload(
            user=self.user,
            product=self.product,
            environment=BillingProduct.Environment.SANDBOX,
        )
        self.webhook_url = reverse("billing:paddle_webhook")

    def test_checkout_page_uses_sandbox_token_and_mapped_price(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("billing:overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://cdn.paddle.com/paddle/v2/paddle.js")
        self.assertContains(response, "pri_sandbox_basic_monthly")
        self.assertContains(response, "test_client_token")
        self.assertNotContains(response, "Mercado Pago")

    def test_checkout_fails_closed_when_provider_price_drifted(self):
        self.product.amount_minor = 1
        self.product.save(update_fields=["amount_minor", "updated_at"])

        with self.assertRaises(PaddleCheckoutUnavailable):
            build_paddle_checkout_payload(
                user=self.user,
                product=self.product,
                environment=BillingProduct.Environment.SANDBOX,
            )

    def test_subscription_webhook_is_verified_idempotent_and_projects_access(self):
        payload = self._subscription_payload(event_id="evt_subscription_1")

        response = self._post(payload)
        duplicate = self._post(payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(duplicate.status_code, 200)
        subscription = ProviderSubscription.objects.get(external_subscription_id="sub_sandbox_1")
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.product, self.product)
        self.assertEqual(subscription.status, ProviderSubscription.Status.AUTHORIZED)
        self.assertEqual(subscription.metadata["paddle_customer_id"], "ctm_sandbox_1")
        self.assertEqual(AccountSubscription.objects.get(user=self.user).plan, self.plan)
        self.assertEqual(BillingEvent.objects.count(), 1)

    def test_completed_transaction_records_payment_without_openfactura_document(self):
        self._post(self._subscription_payload(event_id="evt_subscription_2"))
        payload = {
            "event_id": "evt_transaction_1",
            "event_type": "transaction.completed",
            "occurred_at": "2026-09-11T12:00:00Z",
            "data": {
                "id": "txn_sandbox_1",
                "status": "completed",
                "subscription_id": "sub_sandbox_1",
                "currency_code": "CLP",
                "billed_at": "2026-09-11T12:00:00Z",
                "details": {"totals": {"total": "7990"}},
                "items": [{"price": {"id": self.product.external_price_id}}],
                "custom_data": {
                    "myscoope_checkout_reference": self.checkout.checkout_reference,
                },
            },
        }

        response = self._post(payload)

        self.assertEqual(response.status_code, 200)
        payment = BillingPayment.objects.get(external_payment_id="txn_sandbox_1")
        self.assertEqual(payment.provider, PaymentProvider.PADDLE)
        self.assertEqual(payment.amount_minor, 7_990)
        self.assertEqual(payment.status, BillingPayment.Status.APPROVED)
        self.assertFalse(TaxDocument.objects.filter(payment=payment).exists())

    def test_invalid_signature_is_rejected_before_persistence(self):
        body = json.dumps(self._subscription_payload(event_id="evt_invalid")).encode()

        response = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_PADDLE_SIGNATURE="ts=1;h1=invalid",
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(BillingEvent.objects.filter(external_event_id="evt_invalid").exists())

    def test_approved_full_refund_revokes_access_without_tax_document(self):
        self._post(self._subscription_payload(event_id="evt_subscription_refund"))
        self._post({
            "event_id": "evt_transaction_refund",
            "event_type": "transaction.completed",
            "data": {
                "id": "txn_refund",
                "status": "completed",
                "subscription_id": "sub_sandbox_1",
                "currency_code": "CLP",
                "billed_at": "2026-09-11T12:00:00Z",
                "details": {"totals": {"total": "7990"}},
                "items": [{"price": {"id": self.product.external_price_id}}],
            },
        })
        refund = {
            "event_id": "evt_adjustment_refund",
            "event_type": "adjustment.updated",
            "data": {
                "id": "adj_refund",
                "transaction_id": "txn_refund",
                "subscription_id": "sub_sandbox_1",
                "action": "refund",
                "type": "full",
                "status": "approved",
                "currency_code": "CLP",
                "totals": {"total": "7990"},
            },
        }

        response = self._post(refund)

        self.assertEqual(response.status_code, 200)
        payment = BillingPayment.objects.get(external_payment_id="txn_refund")
        subscription = ProviderSubscription.objects.get(external_subscription_id="sub_sandbox_1")
        account_subscription = AccountSubscription.objects.get(user=self.user)
        self.assertEqual(payment.status, BillingPayment.Status.REFUNDED)
        self.assertEqual(subscription.status, ProviderSubscription.Status.PAST_DUE)
        self.assertEqual(account_subscription.status, AccountSubscription.Status.PAST_DUE)
        self.assertFalse(TaxDocument.objects.filter(payment=payment).exists())

    def test_webhook_is_hidden_when_disabled(self):
        with override_settings(BILLING_PADDLE_WEBHOOK_ENABLED=False):
            response = self._post(self._subscription_payload(event_id="evt_disabled"))

        self.assertEqual(response.status_code, 404)

    def test_authenticated_user_can_open_a_temporary_paddle_portal_session(self):
        self._post(self._subscription_payload(event_id="evt_subscription_portal"))
        subscription = ProviderSubscription.objects.get(external_subscription_id="sub_sandbox_1")
        gateway = _FakePaddleGateway()
        self.client.force_login(self.user)

        with patch("billing.interface.views.build_paddle_gateway", return_value=gateway):
            response = self.client.post(reverse("billing:paddle_customer_portal", args=(subscription.pk,)))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://customer-portal.paddle.com/session?token=temporary")
        self.assertEqual(gateway.calls, [("ctm_sandbox_1", "sub_sandbox_1")])

    def _subscription_payload(self, *, event_id: str):
        return {
            "event_id": event_id,
            "event_type": "subscription.created",
            "occurred_at": "2026-09-11T12:00:00Z",
            "data": {
                "id": "sub_sandbox_1",
                "status": "active",
                "customer_id": "ctm_sandbox_1",
                "transaction_id": "txn_sandbox_initial",
                "items": [{"price": {"id": self.product.external_price_id}}],
                "custom_data": {
                    "myscoope_checkout_reference": self.checkout.checkout_reference,
                },
                "current_billing_period": {
                    "starts_at": "2026-09-11T12:00:00Z",
                    "ends_at": "2026-10-11T12:00:00Z",
                },
                "scheduled_change": None,
            },
        }

    def _post(self, payload):
        body = json.dumps(payload, separators=(",", ":")).encode()
        timestamp = int(time.time())
        return self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_PADDLE_SIGNATURE=_signature(body, timestamp=timestamp),
        )


def _signature(body: bytes, *, timestamp: int) -> str:
    digest = hmac.new(
        PADDLE_SECRET.encode(),
        str(timestamp).encode() + b":" + body,
        hashlib.sha256,
    ).hexdigest()
    return f"ts={timestamp};h1={digest}"


class _FakeResponse:
    def __init__(self, payload, *, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class _FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response


class _FakePaddleGateway:
    def __init__(self):
        self.calls = []

    def create_customer_portal_session(self, *, customer_id, subscription_id):
        self.calls.append((customer_id, subscription_id))
        return PaddlePortalLinks(
            overview="https://customer-portal.paddle.com/session?token=temporary",
            cancel_subscription="https://customer-portal.paddle.com/session?action=cancel",
            update_payment_method="https://customer-portal.paddle.com/session?action=payment",
        )
