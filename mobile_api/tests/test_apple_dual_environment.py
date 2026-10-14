from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

from billing.application.contracts import AppleTransactionEvidence
from billing.models import (
    AppleAppAccountToken,
    AppleSandboxAccess,
    BillingProduct,
    PaymentProvider,
    ProviderSubscription,
)
from accounts.models import AccountPlan, AccountSubscription
from billing.application.contracts import AppleSubscriptionStatusEvidence
from billing.infrastructure.providers.apple_app_store import AppleAppStoreClient
from appstoreserverlibrary.signed_data_verifier import VerificationException, VerificationStatus
from mobile_api.tests.base import AuthenticatedMobileAPITestCase


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIAppleDualEnvironmentTests(AuthenticatedMobileAPITestCase):
    @override_settings(BILLING_APPLE_PURCHASES_ENABLED=True)
    def test_temporary_signature_verification_failure_is_retryable_for_both_product_kinds(self):
        from unittest.mock import Mock
        gateway = AppleAppStoreClient.__new__(AppleAppStoreClient)
        gateway.verifier = Mock()
        gateway.verifier.verify_and_decode_signed_transaction.side_effect = VerificationException(VerificationStatus.RETRYABLE_VERIFICATION_FAILURE)
        for path in ("/api/v1/subscriptions/apple/transactions", "/api/v1/credit-packs/apple/transactions"):
            with self.subTest(path=path), patch("mobile_api.apple_billing.build_apple_app_store_gateway", return_value=gateway):
                response = self.client.post(path, data={"signed_transaction": "header.payload.signature"}, content_type="application/json")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["error"]["code"], "apple_billing_unavailable")
        self.assertFalse(ProviderSubscription.objects.filter(user=self.user).exists())
        self.assertEqual(AccountSubscription.objects.get(user=self.user).plan.slug, "free")

    @override_settings(BILLING_APPLE_PURCHASES_ENABLED=True)
    def test_upgrade_response_contains_the_new_effective_plan_and_benefits(self):
        product = BillingProduct.objects.create(provider="apple_app_store", environment="sandbox",
            external_product_id="pro.upgrade", account_plan=AccountPlan.objects.get(slug="pro"), amount_minor=0)
        token = AppleAppAccountToken.objects.create(user=self.user)
        evidence = AppleTransactionEvidence(original_transaction_id="upgrade", transaction_id="upgrade-1",
            product_id=product.external_product_id, app_account_token=str(token.token), environment="Sandbox",
            expires_date=timezone.now() + timedelta(days=30), ownership_type="PURCHASED")
        with patch("mobile_api.apple_billing.build_apple_app_store_gateway", return_value=SimpleNamespace(verify_transaction=lambda value: evidence)):
            response = self.client.post("/api/v1/subscriptions/apple/transactions",
                data={"signed_transaction": "header.payload.signature"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual((data["plan_name"], data["entitlements"]["plan_name"]), ("Pro", "Pro"))
        self.assertEqual(data["entitlements"]["included_monthly_credits"], 1000)
        self.assertEqual(data["evidence"][0]["product_id"], "pro.upgrade")

    @override_settings(BILLING_APPLE_PURCHASES_ENABLED=True)
    def test_restoring_an_authoritative_receipt_after_expiry_reports_inactive_benefits(self):
        product = BillingProduct.objects.create(provider="apple_app_store", environment="sandbox",
            external_product_id="pro.expired-restore", account_plan=AccountPlan.objects.get(slug="pro"), amount_minor=0)
        token = AppleAppAccountToken.objects.create(user=self.user)
        evidence = AppleTransactionEvidence(original_transaction_id="expired-restore", transaction_id="expired-restore-1",
            product_id=product.external_product_id, app_account_token=str(token.token), environment="Sandbox",
            expires_date=timezone.now() - timedelta(seconds=1), ownership_type="PURCHASED")
        # Simulate an authoritative active row whose deadline passes while the
        # device is offline and before the expiration notification is delivered.
        ProviderSubscription.objects.create(provider="apple_app_store", external_subscription_id="expired-restore",
            user=self.user, product=product, status="authorized", current_period_end=evidence.expires_date,
            metadata={"apple_latest_transaction_id": evidence.transaction_id, "apple_evidence_source": "app_store_server_api"})
        AccountSubscription.objects.filter(user=self.user).update(plan=product.account_plan,
            current_period_end=evidence.expires_date)
        with patch("mobile_api.apple_billing.build_apple_app_store_gateway", return_value=SimpleNamespace(verify_transaction=lambda value: evidence)):
            response = self.client.post("/api/v1/subscriptions/apple/transactions",
                data={"signed_transaction": "header.payload.signature"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual((data["transaction_status"], data["entitlements"]["plan_name"]), ("inactive", "Free"))
        self.assertEqual(ProviderSubscription.objects.get(user=self.user).status, "expired")

    def test_reconciliation_reads_current_apple_status_and_updates_this_account_only(self):
        product = BillingProduct.objects.create(provider="apple_app_store", environment="sandbox",
            external_product_id="pro.reconcile", account_plan=AccountPlan.objects.get(slug="pro"), amount_minor=0)
        token = AppleAppAccountToken.objects.create(user=self.user)
        ProviderSubscription.objects.create(provider="apple_app_store", external_subscription_id="reconcile",
            user=self.user, product=product, status="authorized")
        evidence = AppleTransactionEvidence(original_transaction_id="reconcile", transaction_id="reconcile-1",
            product_id=product.external_product_id, app_account_token=str(token.token), environment="Sandbox",
            expires_date=timezone.now() + timedelta(days=30), ownership_type="PURCHASED",
            metadata={"apple_next_product_id": "basic.annual"})
        gateway = SimpleNamespace(get_subscription_statuses=lambda value: (AppleSubscriptionStatusEvidence(status="active", transaction=evidence),))
        with patch("mobile_api.apple_billing.build_apple_app_store_gateway", return_value=gateway) as build:
            response = self.client.post("/api/v1/subscriptions/apple/reconcile")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual((data["plan_name"], data["entitlements"]["plan_name"]), ("Pro", "Pro"))
        self.assertEqual(data["evidence"][0]["next_product_id"], "basic.annual")
        build.assert_called_once_with(environment="sandbox")

    def test_reconciliation_provider_failure_is_retryable_and_keeps_existing_access(self):
        product = BillingProduct.objects.create(provider="apple_app_store", environment="sandbox",
            external_product_id="pro.failed-reconcile", account_plan=AccountPlan.objects.get(slug="pro"), amount_minor=0)
        ProviderSubscription.objects.create(provider="apple_app_store", external_subscription_id="reconcile-failed",
            user=self.user, product=product, status="authorized")
        AccountSubscription.objects.filter(user=self.user).update(plan=product.account_plan)
        with patch("mobile_api.apple_billing.build_apple_app_store_gateway", side_effect=RuntimeError("private provider failure")):
            response = self.client.post("/api/v1/subscriptions/apple/reconcile")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private provider failure", response.content.decode())
        self.assertEqual(AccountSubscription.objects.get(user=self.user).plan.slug, "pro")

    @override_settings(BILLING_APPLE_PURCHASES_ENABLED=True)
    def test_apple_transaction_is_verified_server_side_before_projection(self):
        plan = self.user.account_subscription.plan
        product = BillingProduct.objects.create(
            provider=PaymentProvider.APPLE_APP_STORE,
            environment=BillingProduct.Environment.SANDBOX,
            external_product_id="com.myscoope.basic.yearly",
            account_plan=plan,
            amount_minor=0,
            interval=BillingProduct.Interval.YEAR,
        )
        token = AppleAppAccountToken.objects.create(user=self.user)
        evidence = AppleTransactionEvidence(
            original_transaction_id="api-original",
            transaction_id="api-transaction",
            product_id=product.external_product_id,
            app_account_token=str(token.token),
            environment="Sandbox",
            expires_date=int((timezone.now() + timedelta(days=365)).timestamp() * 1000),
            ownership_type="PURCHASED",
        )
        gateway = SimpleNamespace(verify_transaction=lambda value: evidence)

        with patch("mobile_api.apple_billing.build_apple_app_store_gateway", return_value=gateway):
            response = self.client.post(
                "/api/v1/subscriptions/apple/transactions",
                data={"signed_transaction": "header.payload.signature"},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ProviderSubscription.objects.filter(
                user=self.user,
                provider=PaymentProvider.APPLE_APP_STORE,
                status=ProviderSubscription.Status.AUTHORIZED,
            ).exists()
        )

    @override_settings(BILLING_APPLE_PURCHASES_ENABLED=True)
    def test_overview_exposes_only_the_configured_apple_environment(self):
        plan = self.user.account_subscription.plan
        for environment in (BillingProduct.Environment.SANDBOX, BillingProduct.Environment.LIVE):
            BillingProduct.objects.create(
                provider=PaymentProvider.APPLE_APP_STORE,
                environment=environment,
                external_product_id="com.myscoope.basic.monthly",
                account_plan=plan,
                amount_minor=0,
            )

        response = self.client.get("/api/v1/subscriptions")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["products"]), 1)

    @override_settings(BILLING_APPLE_PURCHASES_ENABLED=True, BILLING_APPLE_ENVIRONMENT="invalid")
    def test_invalid_apple_environment_exposes_no_products(self):
        plan = self.user.account_subscription.plan
        BillingProduct.objects.create(
            provider=PaymentProvider.APPLE_APP_STORE,
            environment=BillingProduct.Environment.LIVE,
            external_product_id="com.myscoope.invalid-environment",
            account_plan=plan,
            amount_minor=0,
        )

        response = self.client.get("/api/v1/subscriptions")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["data"]["purchases_enabled"])
        self.assertEqual(response.json()["data"]["products"], [])

    @override_settings(
        BILLING_APPLE_PURCHASES_ENABLED=False,
        BILLING_APPLE_SANDBOX_PURCHASES_ENABLED=True,
        BILLING_APPLE_ENVIRONMENT="production",
    )
    def test_live_disabled_verifies_sandbox_directly_only_for_authorized_account(self):
        plan = self.user.account_subscription.plan
        product = BillingProduct.objects.create(
            provider=PaymentProvider.APPLE_APP_STORE,
            environment=BillingProduct.Environment.SANDBOX,
            external_product_id="com.myscoope.review.monthly",
            account_plan=plan,
            amount_minor=0,
        )
        token = AppleAppAccountToken.objects.create(user=self.user)
        evidence = AppleTransactionEvidence(
            original_transaction_id="review-original",
            transaction_id="review-transaction",
            product_id=product.external_product_id,
            app_account_token=str(token.token),
            environment="Sandbox",
            expires_date=int((timezone.now() + timedelta(days=30)).timestamp() * 1000),
            ownership_type="PURCHASED",
        )
        sandbox_gateway = SimpleNamespace(verify_transaction=lambda value: evidence)
        body = {"signed_transaction": "header.payload.signature"}

        rejected = self.client.post(
            "/api/v1/subscriptions/apple/transactions",
            data=body,
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 403)

        AppleSandboxAccess.objects.create(user=self.user, purpose=AppleSandboxAccess.Purpose.APP_REVIEW)
        overview = self.client.get("/api/v1/subscriptions")
        self.assertEqual(overview.status_code, 200)
        self.assertTrue(overview.json()["data"]["purchases_enabled"])
        self.assertEqual(
            [item["product_id"] for item in overview.json()["data"]["products"]],
            [product.external_product_id],
        )
        with patch(
            "mobile_api.apple_billing.build_apple_app_store_gateway",
            return_value=sandbox_gateway,
        ) as builder:
            accepted = self.client.post(
                "/api/v1/subscriptions/apple/transactions",
                data=body,
                content_type="application/json",
            )
        self.assertEqual(accepted.status_code, 200)
        builder.assert_called_once_with(environment="sandbox")

    @override_settings(
        BILLING_APPLE_PURCHASES_ENABLED=False,
        BILLING_APPLE_SANDBOX_PURCHASES_ENABLED=True,
        BILLING_APPLE_ENVIRONMENT="production",
    )
    def test_sandbox_access_cannot_bypass_the_live_kill_switch_for_either_product_kind(self):
        token = AppleAppAccountToken.objects.create(user=self.user)
        AppleSandboxAccess.objects.create(user=self.user, purpose=AppleSandboxAccess.Purpose.INTERNAL)
        evidence = AppleTransactionEvidence(original_transaction_id="live-disabled", transaction_id="live-disabled-1",
            product_id="production.product", app_account_token=str(token.token), environment="Production",
            expires_date=timezone.now() + timedelta(days=30), ownership_type="PURCHASED")
        gateway = SimpleNamespace(verify_transaction=lambda value: evidence)
        for path in ("/api/v1/subscriptions/apple/transactions", "/api/v1/credit-packs/apple/transactions"):
            with self.subTest(path=path), patch("mobile_api.apple_billing.build_apple_app_store_gateway", return_value=gateway) as builder:
                response = self.client.post(path, data={"signed_transaction": "header.payload.signature"}, content_type="application/json")
                self.assertEqual(response.status_code, 422)
                builder.assert_called_once_with(environment="sandbox")
        self.assertFalse(ProviderSubscription.objects.filter(user=self.user).exists())
        self.assertEqual(AccountSubscription.objects.get(user=self.user).plan.slug, "free")
