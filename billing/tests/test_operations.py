from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription
from billing.application.contracts import ProviderPaymentSnapshot, ProviderSubscriptionSnapshot
from billing.application.services.openfactura import issue_tax_document, reconcile_tax_document
from billing.application.services.provider_sync import sync_provider_payment, sync_provider_subscription
from billing.infrastructure.providers.fake import FakeTaxDocumentGateway
from billing.infrastructure.providers.openfactura import OpenFacturaClient
from billing.models import BillingPayment, BillingProduct, PaymentProvider, ProviderSubscription, TaxDocument

ISSUER = {"RUTEmisor": "76000000-0", "RznSocEmisor": "My Scoope", "GiroEmisor": "Software"}


class _Response:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class _Session:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return _Response(self.payload)


class OpenFacturaClientTests(SimpleTestCase):
    def test_issue_uses_api_key_and_persistent_idempotency_header(self):
        session = _Session({"token": "of-token", "folio": 42})
        client = OpenFacturaClient(api_key="secret", base_url="https://of.example", session=session)

        result = client.issue_document(idempotency_key="idem-1", payload={"dte": {}})

        self.assertEqual(result.document_token, "of-token")
        method, url, kwargs = session.calls[0]
        self.assertEqual((method, url), ("POST", "https://of.example/v2/dte/document"))
        self.assertEqual(kwargs["headers"]["Idempotency-Key"], "idem-1")
        self.assertEqual(kwargs["headers"]["apikey"], "secret")

    def test_status_is_normalized_from_openfactura_spanish_state(self):
        client = OpenFacturaClient(
            api_key="secret", base_url="https://of.example", session=_Session({"status": "Aceptado con Reparo"})
        )
        self.assertEqual(client.get_document_status("token").status, TaxDocument.Status.ACCEPTED_WITH_OBJECTIONS)


class BillingOperationsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="billing-ops", email="ops@example.com")
        self.plan = AccountPlan.objects.create(slug="ops", name="Ops", status=AccountPlan.Status.ACTIVE)
        self.product = BillingProduct.objects.create(
            provider=PaymentProvider.MERCADO_PAGO,
            external_product_id="plan-ops",
            account_plan=self.plan,
            amount_minor=12990,
        )
        self.subscription = ProviderSubscription.objects.create(
            user=self.user,
            product=self.product,
            provider=PaymentProvider.MERCADO_PAGO,
            external_subscription_id="sub-ops",
        )

    def _approved_payment(self):
        sync_provider_subscription(ProviderSubscriptionSnapshot(
            provider=PaymentProvider.MERCADO_PAGO,
            external_subscription_id="sub-ops",
            external_product_id="plan-ops",
            status=ProviderSubscription.Status.AUTHORIZED,
        ))
        return sync_provider_payment(ProviderPaymentSnapshot(
            provider=PaymentProvider.MERCADO_PAGO,
            external_payment_id="pay-ops",
            external_subscription_id="sub-ops",
            status=BillingPayment.Status.APPROVED,
            amount_minor=12990,
            currency="CLP",
            approved_at=timezone.now(),
        ))

    def test_issue_and_status_reconciliation_are_persisted(self):
        payment = self._approved_payment()
        document = payment.tax_document
        gateway = FakeTaxDocumentGateway()

        issued = issue_tax_document(document=document, gateway=gateway, issuer=ISSUER)
        accepted = reconcile_tax_document(document=issued, gateway=gateway)

        self.assertEqual(issued.attempts, 1)
        self.assertEqual(accepted.status, TaxDocument.Status.ACCEPTED)
        self.assertTrue(accepted.document_token)
        self.assertEqual(gateway.calls[0][1]["dte"]["Encabezado"]["IdDoc"]["TipoDTE"], 39)

    def test_retry_after_idempotency_window_requires_manual_reconciliation(self):
        payment = self._approved_payment()
        document = payment.tax_document
        document.first_attempt_at = timezone.now() - timedelta(hours=24)
        document.status = TaxDocument.Status.FAILED
        document.save()

        result = issue_tax_document(document=document, gateway=FakeTaxDocumentGateway(), issuer=ISSUER)

        self.assertEqual(result.status, TaxDocument.Status.FAILED)
        self.assertIn("reconcile manually", result.last_error)

    def test_refund_revokes_access_and_flags_tax_review_without_deleting_evidence(self):
        self._approved_payment()

        payment = sync_provider_payment(ProviderPaymentSnapshot(
            provider=PaymentProvider.MERCADO_PAGO,
            external_payment_id="pay-ops",
            external_subscription_id="sub-ops",
            status=BillingPayment.Status.REFUNDED,
            amount_minor=12990,
            currency="CLP",
        ))

        self.assertEqual(payment.status, BillingPayment.Status.REFUNDED)
        self.assertTrue(payment.tax_document.adjustment_required)
        self.assertEqual(AccountSubscription.objects.get(user=self.user).status, AccountSubscription.Status.PAST_DUE)

    def test_operational_commands_offer_read_only_dry_run(self):
        self._approved_payment()
        call_command("issue_tax_documents", dry_run=True, limit=10)
        call_command("reconcile_billing", dry_run=True, limit=10)
