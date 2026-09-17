from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

from billing.application.contracts import GooglePlaySubscriptionEvidence
from billing.application.services.google_play import google_play_account_id
from billing.models import BillingProduct, PaymentProvider, ProviderSubscription
from mobile_api.tests.base import AuthenticatedMobileAPITestCase


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False, BILLING_GOOGLE_PLAY_PURCHASES_ENABLED=True)
class GooglePlayBillingAPITests(AuthenticatedMobileAPITestCase):
    def test_purchase_is_verified_server_side_before_projection(self):
        plan = self.user.account_subscription.plan
        product = BillingProduct.objects.create(
            provider=PaymentProvider.GOOGLE_PLAY,
            external_product_id="myscoope_basic",
            external_price_id="monthly",
            account_plan=plan,
            amount_minor=7_990,
        )
        evidence = GooglePlaySubscriptionEvidence(
            purchase_token="play-purchase-token-123",
            product_id=product.external_product_id,
            base_plan_id=product.external_price_id,
            status="SUBSCRIPTION_STATE_ACTIVE",
            expiry_time=(timezone.now() + timedelta(days=30)).isoformat(),
            obfuscated_account_id=google_play_account_id(self.user),
            auto_renewing=True,
        )
        gateway = SimpleNamespace(verify_subscription=lambda value: evidence)
        with patch("mobile_api.routes.google_play_billing.build_google_play_gateway", return_value=gateway):
            response = self.client.post(
                "/api/v1/subscriptions/google-play/purchases",
                data={"purchase_token": evidence.purchase_token},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        subscription = ProviderSubscription.objects.get(
            provider=PaymentProvider.GOOGLE_PLAY,
            external_subscription_id=evidence.purchase_token,
        )
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.status, ProviderSubscription.Status.AUTHORIZED)
