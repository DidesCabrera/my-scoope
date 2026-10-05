from django.test import override_settings

from billing.models import AppleAppAccountToken, BillingProduct, PaymentProvider
from mobile_api.tests.base import AuthenticatedMobileAPITestCase


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIBillingTests(AuthenticatedMobileAPITestCase):
    def test_subscription_overview_is_consumer_only_and_uses_configured_apple_products(self):
        plan = self.user.account_subscription.plan
        product = BillingProduct.objects.create(
            provider=PaymentProvider.APPLE_APP_STORE,
            environment=BillingProduct.Environment.SANDBOX,
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
                    "provider": PaymentProvider.APPLE_APP_STORE,
                    "base_plan_id": "",
                    "plan_name": plan.name,
                    "interval": "month",
                }
            ],
        )
        self.assertNotIn("price", data["products"][0])
        self.assertTrue(AppleAppAccountToken.objects.filter(user=self.user).exists())
