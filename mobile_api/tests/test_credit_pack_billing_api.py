"""Consumable purchase contract on the mobile billing API."""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import override_settings

from accounts.models import AccountPlan, AccountSubscription, CreditWallet
from billing.application.contracts import AppleTransactionEvidence
from billing.application.services.credit_packs import configure_credit_pack_product
from billing.models import AppleAppAccountToken, CreditPackPurchase, PaymentProvider
from mobile_api.tests.base import AuthenticatedMobileAPITestCase


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPICreditPackBillingTests(AuthenticatedMobileAPITestCase):
    @override_settings(BILLING_APPLE_PURCHASES_ENABLED=True)
    def test_credit_packs_are_offered_only_to_paid_accounts(self):
        configure_credit_pack_product(
            provider=PaymentProvider.APPLE_APP_STORE, environment="sandbox",
            offer_code="credits-500", external_product_id="com.myscoope.credits.500",
        )
        free = self.client.get("/api/v1/subscriptions").json()["data"]
        self.assertFalse(free["can_buy_credit_packs"])
        # Keep product identity available to finish an in-flight purchase after downgrade.
        self.assertEqual(free["credit_packs"][0]["credits"], 500)
        AccountSubscription.objects.update_or_create(
            user=self.user, defaults={"plan": AccountPlan.objects.get(slug="basic")},
        )
        paid = self.client.get("/api/v1/subscriptions").json()["data"]
        self.assertTrue(paid["can_buy_credit_packs"])
        self.assertEqual(paid["credit_packs"][0]["credits"], 500)

    @override_settings(BILLING_APPLE_PURCHASES_ENABLED=True)
    def test_verified_apple_consumable_grants_credit_pack_once(self):
        configure_credit_pack_product(
            provider=PaymentProvider.APPLE_APP_STORE, environment="sandbox",
            offer_code="credits-500", external_product_id="com.myscoope.credits.500",
        )
        AccountSubscription.objects.update_or_create(
            user=self.user, defaults={"plan": AccountPlan.objects.get(slug="basic")},
        )
        overview = self.client.get("/api/v1/subscriptions")
        self.assertEqual(overview.status_code, 200)
        token = AppleAppAccountToken.objects.get(user=self.user)
        evidence = AppleTransactionEvidence(
            original_transaction_id="pack-original", transaction_id="pack-transaction",
            product_id="com.myscoope.credits.500", app_account_token=str(token.token),
            environment="Sandbox", ownership_type="PURCHASED",
        )
        gateway = SimpleNamespace(verify_transaction=lambda value: evidence)
        with patch("mobile_api.routes.credit_packs.build_apple_app_store_gateway", return_value=gateway):
            for _ in range(2):
                response = self.client.post(
                    "/api/v1/credit-packs/apple/transactions",
                    data={"signed_transaction": "header.payload.signature"}, content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
        self.assertEqual(CreditPackPurchase.objects.count(), 1)
        self.assertEqual(CreditWallet.objects.get(user=self.user).purchased_balance, 500)
