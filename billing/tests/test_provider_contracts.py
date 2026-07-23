import hashlib
import hmac
import json
import time
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from accounts.models import AccountPlan, AccountSubscription
from billing.models import (
    BillingEvent,
    BillingPayment,
    BillingProduct,
    PaymentProvider,
    ProviderSubscription,
    TaxDocument,
)
from billing.application.contracts import ProviderPaymentSnapshot, ProviderSubscriptionSnapshot
from billing.infrastructure.providers.fake import FakePaymentGateway, FakeTaxDocumentGateway
from billing.infrastructure.providers.mercado_pago import MercadoPagoClient, MercadoPagoProviderError
from billing.infrastructure.providers.mercado_pago_webhooks import (
    InvalidMercadoPagoSignature,
    verify_mercado_pago_signature,
)


SECRET = "webhook-test-secret"


def _signature(*, data_id: str, request_id: str, timestamp: int, secret: str = SECRET) -> str:
    normalized = data_id.lower() if data_id.isalnum() else data_id
    manifest = f"id:{normalized};request-id:{request_id};ts:{timestamp};"
    digest = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f"ts={timestamp},v1={digest}"


class MercadoPagoSignatureTests(SimpleTestCase):
    def test_signature_matches_official_manifest_and_accepts_millisecond_timestamp(self):
        timestamp_ms = 1_785_000_000_000
        result = verify_mercado_pago_signature(
            signature_header=_signature(data_id="ABC123", request_id="req-1", timestamp=timestamp_ms),
            request_id="req-1",
            data_id="ABC123",
            secret=SECRET,
            now_seconds=1_785_000_000,
        )

        self.assertEqual(result.timestamp, timestamp_ms)

    def test_signature_uses_constant_contract_and_rejects_tampering(self):
        timestamp = 1_785_000_000
        with self.assertRaises(InvalidMercadoPagoSignature):
            verify_mercado_pago_signature(
                signature_header=_signature(data_id="123", request_id="req-1", timestamp=timestamp),
                request_id="req-1",
                data_id="999",
                secret=SECRET,
                now_seconds=timestamp,
            )

    def test_signature_rejects_replay_outside_tolerance(self):
        timestamp = 1_785_000_000
        with self.assertRaises(InvalidMercadoPagoSignature):
            verify_mercado_pago_signature(
                signature_header=_signature(data_id="123", request_id="req-1", timestamp=timestamp),
                request_id="req-1",
                data_id="123",
                secret=SECRET,
                tolerance_seconds=300,
                now_seconds=timestamp + 301,
            )


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class _FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, method, url, **kwargs):
        kwargs["method"] = method
        self.calls.append((url, kwargs))
        return self.response


class MercadoPagoClientTests(SimpleTestCase):
    def test_subscription_is_normalized_without_treating_agreement_end_as_current_period(self):
        session = _FakeSession(_FakeResponse({
            "id": "preapproval-1",
            "preapproval_plan_id": "plan-1",
            "status": "authorized",
            "next_payment_date": "2026-08-19T12:00:00Z",
            "auto_recurring": {
                "start_date": "2026-07-19T12:00:00Z",
                "end_date": "2027-07-19T12:00:00Z",
            },
        }))
        client = MercadoPagoClient(access_token="token", base_url="https://api.example", session=session)

        snapshot = client.get_subscription("preapproval-1")

        self.assertEqual(snapshot.status, ProviderSubscription.Status.AUTHORIZED)
        self.assertIsNone(snapshot.current_period_start)
        self.assertIsNone(snapshot.current_period_end)
        self.assertEqual(snapshot.metadata["agreement_end_date"], "2027-07-19T12:00:00Z")
        self.assertEqual(session.calls[0][0], "https://api.example/preapproval/preapproval-1")
        self.assertNotIn("token", str(session.calls[0][0]))

    def test_payment_normalizes_clp_without_decimal_minor_units(self):
        session = _FakeSession(_FakeResponse({
            "id": 77,
            "preapproval_id": "preapproval-1",
            "status": "approved",
            "transaction_amount": 9990,
            "currency_id": "CLP",
            "date_approved": "2026-07-19T12:00:00Z",
        }))
        client = MercadoPagoClient(access_token="token", base_url="https://api.example", session=session)

        snapshot = client.get_payment("77")

        self.assertEqual(snapshot.amount_minor, 9990)
        self.assertEqual(snapshot.status, BillingPayment.Status.APPROVED)

    def test_provider_error_does_not_expose_response_body_or_token(self):
        session = _FakeSession(_FakeResponse({"message": "sensitive"}, status_code=500))
        client = MercadoPagoClient(access_token="secret-token", base_url="https://api.example", session=session)

        with self.assertRaises(MercadoPagoProviderError) as raised:
            client.get_payment("77")

        self.assertNotIn("sensitive", str(raised.exception))
        self.assertNotIn("secret-token", str(raised.exception))


@override_settings(
    BILLING_MERCADOPAGO_WEBHOOK_ENABLED=True,
    BILLING_MERCADOPAGO_ACCESS_TOKEN="test-token",
    BILLING_MERCADOPAGO_WEBHOOK_SECRET=SECRET,
    BILLING_MERCADOPAGO_WEBHOOK_TOLERANCE_SECONDS=300,
)
class MercadoPagoWebhookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mp-user", password="test-pass")
        self.plan = AccountPlan.objects.create(slug="basic-mp", name="Basic MP", status=AccountPlan.Status.ACTIVE)
        self.product = BillingProduct.objects.create(
            provider=PaymentProvider.MERCADO_PAGO,
            external_product_id="mp-plan-basic",
            account_plan=self.plan,
            amount_minor=9990,
        )
        self.subscription = ProviderSubscription.objects.create(
            user=self.user,
            product=self.product,
            provider=PaymentProvider.MERCADO_PAGO,
            external_subscription_id="preapproval-1",
        )
        self.url = reverse("billing:mercado_pago_webhook")

    def _post(self, payload, *, data_id=None, signature=None, request_id="req-1"):
        data_id = str(data_id or payload.get("data", {}).get("id", ""))
        timestamp = int(time.time())
        signature = signature or _signature(data_id=data_id, request_id=request_id, timestamp=timestamp)
        return self.client.post(
            f"{self.url}?data.id={data_id}",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_SIGNATURE=signature,
            HTTP_X_REQUEST_ID=request_id,
        )

    def test_webhook_is_hidden_when_disabled(self):
        with override_settings(BILLING_MERCADOPAGO_WEBHOOK_ENABLED=False):
            response = self._post({"id": 1, "type": "payment", "data": {"id": "77"}})

        self.assertEqual(response.status_code, 404)
        self.assertFalse(BillingEvent.objects.exists())

    def test_invalid_signature_is_rejected_before_event_persistence(self):
        response = self._post(
            {"id": 1, "type": "payment", "data": {"id": "77"}},
            signature="ts=1,v1=invalid",
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(BillingEvent.objects.exists())

    def test_subscription_webhook_fetches_provider_state_then_projects_accounts(self):
        gateway = FakePaymentGateway(subscriptions={
            "preapproval-1": ProviderSubscriptionSnapshot(
                provider=PaymentProvider.MERCADO_PAGO,
                external_subscription_id="preapproval-1",
                external_product_id="mp-plan-basic",
                status=ProviderSubscription.Status.AUTHORIZED,
            )
        })
        payload = {"id": 1001, "type": "subscription_preapproval", "data": {"id": "preapproval-1"}}

        with patch("billing.interface.views.build_mercado_pago_gateway", return_value=gateway):
            response = self._post(payload)
            duplicate = self._post(payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(gateway.calls, [("get_subscription", "preapproval-1")])
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, ProviderSubscription.Status.AUTHORIZED)
        account_subscription = AccountSubscription.objects.get(user=self.user)
        self.assertEqual(account_subscription.plan, self.plan)
        self.assertEqual(account_subscription.source, AccountSubscription.Source.BILLING)
        self.assertEqual(BillingEvent.objects.count(), 1)

    def test_approved_payment_creates_payment_and_one_tax_outbox_row(self):
        gateway = FakePaymentGateway(payments={
            "77": ProviderPaymentSnapshot(
                provider=PaymentProvider.MERCADO_PAGO,
                external_payment_id="77",
                external_subscription_id="preapproval-1",
                status=BillingPayment.Status.APPROVED,
                amount_minor=9990,
                currency="CLP",
            )
        })
        payload = {"id": 1002, "type": "payment", "data": {"id": "77"}}

        with patch("billing.interface.views.build_mercado_pago_gateway", return_value=gateway):
            response = self._post(payload)

        self.assertEqual(response.status_code, 200)
        payment = BillingPayment.objects.get(external_payment_id="77")
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.amount_minor, 9990)
        self.assertTrue(TaxDocument.objects.filter(payment=payment).exists())

    def test_unknown_subscription_is_not_created_from_untrusted_callback_identity(self):
        gateway = FakePaymentGateway(subscriptions={
            "unknown": ProviderSubscriptionSnapshot(
                provider=PaymentProvider.MERCADO_PAGO,
                external_subscription_id="unknown",
                external_product_id="mp-plan-basic",
                status=ProviderSubscription.Status.AUTHORIZED,
            )
        })
        payload = {"id": 1003, "type": "subscription_preapproval", "data": {"id": "unknown"}}

        with patch("billing.interface.views.build_mercado_pago_gateway", return_value=gateway):
            response = self._post(payload)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ProviderSubscription.objects.filter(external_subscription_id="unknown").exists())
        event = BillingEvent.objects.get(external_event_id="1003")
        self.assertEqual(event.status, BillingEvent.Status.IGNORED)


class FakeGatewayTests(SimpleTestCase):
    def test_tax_gateway_reuses_result_for_same_idempotency_key(self):
        gateway = FakeTaxDocumentGateway()

        first = gateway.issue_document(idempotency_key="stable", payload={"total": 9990})
        duplicate = gateway.issue_document(idempotency_key="stable", payload={"total": 9990})

        self.assertEqual(first, duplicate)
        self.assertEqual(first.external_document_id, "fake-1")
