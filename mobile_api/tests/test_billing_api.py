from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

from billing.application.contracts import AppleTransactionEvidence
from billing.models import AppleAppAccountToken, BillingProduct, PaymentProvider, ProviderSubscription
from mobile_api.tests.base import AuthenticatedMobileAPITestCase


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIBillingTests(AuthenticatedMobileAPITestCase):
    def test_subscription_overview_is_consumer_only_and_uses_configured_apple_products(self):
        plan = self.user.account_subscription.plan
        product = BillingProduct.objects.create(
            provider=PaymentProvider.APPLE_APP_STORE,
            external_product_id="com.myscoope.basic.monthly",
            account_plan=plan,
            amount_minor=0,
        )

        with override_settings(BILLING_APPLE_PURCHASES_ENABLED=True):
            response = self.client.get("/api/v1/subscriptions")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertTrue(data["eligible"])
        self.assertTrue(data["purchases_enabled"])
        self.assertEqual(
            data["products"],
            [
                {
                    "product_id": product.external_product_id,
                    "plan_name": plan.name,
                    "interval": "month",
                }
            ],
        )
        self.assertNotIn("price", data["products"][0])
        self.assertTrue(AppleAppAccountToken.objects.filter(user=self.user).exists())

    @override_settings(BILLING_APPLE_PURCHASES_ENABLED=True)
    def test_apple_transaction_is_verified_server_side_before_projection(self):
        plan = self.user.account_subscription.plan
        product = BillingProduct.objects.create(
            provider=PaymentProvider.APPLE_APP_STORE,
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
            expires_date=int((timezone.now() + timedelta(days=365)).timestamp() * 1000),
            ownership_type="PURCHASED",
        )
        gateway = SimpleNamespace(verify_transaction=lambda value: evidence)

        with patch("mobile_api.routes.billing.build_apple_app_store_gateway", return_value=gateway):
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
