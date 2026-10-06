from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from accounts.seed_plans import seed_account_plans
from billing.application.services.catalog import AppleCatalogReference, configure_apple_catalog
from billing.application.services.credit_packs import configure_credit_pack_product
from billing.catalog import seed_billing_offers, seed_credit_pack_offers
from billing.management.commands.check_apple_billing_readiness import (
    PACK_PRODUCTS,
    SUBSCRIPTION_PRODUCTS,
)
from billing.models import AppleSandboxAccess, PaymentProvider


@override_settings(
    BILLING_APPLE_ENVIRONMENT="production",
    BILLING_APPLE_BUNDLE_ID="com.myscoope.app",
    BILLING_APPLE_APP_ID=6804048394,
)
class AppleBillingReadinessTests(TestCase):
    def setUp(self):
        seed_account_plans()
        seed_billing_offers()
        seed_credit_pack_offers()

    def test_missing_catalog_and_test_account_fail_closed(self):
        with self.assertRaisesMessage(CommandError, "live subscriptions mapping"):
            call_command("check_apple_billing_readiness", scenario="all")

    def test_complete_dual_catalog_and_authorized_account_pass(self):
        references = tuple(
            AppleCatalogReference(offer_code=offer_code, product_id=product_id)
            for offer_code, product_id in SUBSCRIPTION_PRODUCTS.items()
        )
        for environment in ("live", "sandbox"):
            configure_apple_catalog(environment=environment, references=references)
            for offer_code, product_id in PACK_PRODUCTS.items():
                configure_credit_pack_product(
                    provider=PaymentProvider.APPLE_APP_STORE,
                    environment=environment,
                    offer_code=offer_code,
                    external_product_id=product_id,
                )
        user = get_user_model().objects.create_user(username="app-review-readiness")
        AppleSandboxAccess.objects.create(
            user=user,
            purpose=AppleSandboxAccess.Purpose.APP_REVIEW,
        )
        output = StringIO()

        call_command("check_apple_billing_readiness", scenario="all", stdout=output)

        self.assertIn("live_catalog=subscriptions:4/4 credit_packs:3/3", output.getvalue())
        self.assertIn("sandbox_catalog=subscriptions:4/4 credit_packs:3/3", output.getvalue())
        self.assertIn("active_sandbox_accounts=1", output.getvalue())
        self.assertIn("Apple billing readiness passed for all", output.getvalue())
