from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import AccountPlan, AccountSubscription
from billing.application.services.events import UnverifiedBillingEvent, receive_verified_billing_event
from billing.application.services.projections import project_provider_subscription
from billing.application.services.tax_documents import PaymentNotApproved, schedule_tax_document
from billing.models import BillingPayment, BillingProduct, PaymentProvider, ProviderSubscription, TaxDocument


class BillingFoundationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="billing-user", password="test-pass")
        self.plan = AccountPlan.objects.create(slug="basic", name="Basic", status=AccountPlan.Status.ACTIVE)
        self.product = BillingProduct.objects.create(
            provider=PaymentProvider.MERCADO_PAGO,
            external_product_id="mp-basic-monthly",
            account_plan=self.plan,
            amount_minor=9990,
        )

    def test_provider_product_identifier_is_unique_per_provider(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            BillingProduct.objects.create(
                provider=PaymentProvider.MERCADO_PAGO,
                external_product_id="mp-basic-monthly",
                account_plan=self.plan,
                amount_minor=10990,
            )

    def test_verified_event_inbox_is_idempotent_and_keeps_first_payload(self):
        first = receive_verified_billing_event(
            provider=PaymentProvider.MERCADO_PAGO,
            external_event_id="request-1:payment:123",
            event_type="payment.updated",
            resource_id="123",
            payload={"data": {"id": "123"}},
            signature_verified=True,
        )
        duplicate = receive_verified_billing_event(
            provider=PaymentProvider.MERCADO_PAGO,
            external_event_id="request-1:payment:123",
            event_type="payment.updated",
            resource_id="123",
            payload={"changed": True},
            signature_verified=True,
        )

        self.assertTrue(first.created)
        self.assertFalse(duplicate.created)
        self.assertEqual(first.event.pk, duplicate.event.pk)
        self.assertEqual(duplicate.event.payload, {"data": {"id": "123"}})

    def test_unverified_event_is_rejected_before_persistence(self):
        with self.assertRaises(UnverifiedBillingEvent):
            receive_verified_billing_event(
                provider=PaymentProvider.MERCADO_PAGO,
                external_event_id="untrusted",
                event_type="payment.updated",
                signature_verified=False,
            )

    def test_authorized_provider_subscription_projects_to_accounts(self):
        provider_subscription = ProviderSubscription.objects.create(
            user=self.user,
            product=self.product,
            provider=PaymentProvider.MERCADO_PAGO,
            external_subscription_id="preapproval-123",
            status=ProviderSubscription.Status.AUTHORIZED,
        )

        projected = project_provider_subscription(provider_subscription)

        self.assertEqual(projected.plan, self.plan)
        self.assertEqual(projected.status, AccountSubscription.Status.ACTIVE)
        self.assertEqual(projected.source, AccountSubscription.Source.BILLING)
        self.assertEqual(projected.metadata["billing_subscription_id"], str(provider_subscription.pk))

    def test_paused_provider_subscription_removes_active_account_access(self):
        provider_subscription = ProviderSubscription.objects.create(
            user=self.user,
            product=self.product,
            provider=PaymentProvider.MERCADO_PAGO,
            external_subscription_id="preapproval-paused",
            status=ProviderSubscription.Status.AUTHORIZED,
        )
        project_provider_subscription(provider_subscription)
        provider_subscription.status = ProviderSubscription.Status.PAUSED
        provider_subscription.save(update_fields=["status", "updated_at"])

        projected = project_provider_subscription(provider_subscription)

        self.assertEqual(projected.status, AccountSubscription.Status.PAST_DUE)
        self.assertFalse(projected.is_active)

    def test_tax_document_outbox_is_one_per_approved_payment(self):
        payment = BillingPayment.objects.create(
            user=self.user,
            provider=PaymentProvider.MERCADO_PAGO,
            external_payment_id="payment-123",
            status=BillingPayment.Status.APPROVED,
            amount_minor=9990,
        )

        first, created = schedule_tax_document(payment=payment, request_payload={"total": 9990})
        duplicate, duplicate_created = schedule_tax_document(payment=payment, request_payload={"total": 1})

        self.assertTrue(created)
        self.assertFalse(duplicate_created)
        self.assertEqual(first.pk, duplicate.pk)
        self.assertEqual(duplicate.request_payload, {"total": 9990})
        self.assertEqual(duplicate.provider, TaxDocument.Provider.OPENFACTURA)

    def test_tax_document_rejects_unapproved_payment(self):
        payment = BillingPayment.objects.create(
            user=self.user,
            provider=PaymentProvider.MERCADO_PAGO,
            external_payment_id="payment-pending",
            status=BillingPayment.Status.PENDING,
            amount_minor=9990,
        )

        with self.assertRaises(PaymentNotApproved):
            schedule_tax_document(payment=payment)
