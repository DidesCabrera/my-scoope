from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.seed_plans import seed_account_plans
from billing.application.services.catalog import AppleCatalogReference, configure_apple_catalog
from billing.catalog import seed_billing_offers
from billing.models import BillingOffer, BillingProduct, PaymentProvider, ProviderSubscription


class AppleLegacyEnvironmentMigrationTests(TestCase):
    def test_expired_sandbox_history_is_reclassified_without_rewriting_its_price(self):
        seed_account_plans()
        seed_billing_offers()
        offer = BillingOffer.objects.get(code="basic-monthly")
        offer.amount_minor = 7_990
        offer.save(update_fields=["amount_minor", "updated_at"])
        references = self._references()
        configure_apple_catalog(environment="live", references=references)
        legacy_product = BillingProduct.objects.get(
            provider=PaymentProvider.APPLE_APP_STORE,
            environment=BillingProduct.Environment.LIVE,
            offer=offer,
        )
        user = get_user_model().objects.create_user(username="legacy_apple_sandbox", password="unused")
        subscription = ProviderSubscription.objects.create(
            user=user,
            product=legacy_product,
            provider=PaymentProvider.APPLE_APP_STORE,
            external_subscription_id="legacy_sandbox_contract",
            status=ProviderSubscription.Status.EXPIRED,
            metadata={"apple_environment": "Sandbox"},
        )
        BillingProduct.objects.filter(provider=PaymentProvider.APPLE_APP_STORE).update(active=False)
        offer.amount_minor = 3_990
        offer.save(update_fields=["amount_minor", "updated_at"])

        migration = import_module(
            "billing.migrations.0009_reclassify_legacy_apple_sandbox_subscriptions"
        )
        migration.reclassify_legacy_sandbox_subscriptions(apps, None)
        configure_apple_catalog(environment="live", references=references)
        configure_apple_catalog(environment="sandbox", references=references)

        subscription.refresh_from_db()
        self.assertEqual(subscription.product.environment, BillingProduct.Environment.SANDBOX)
        self.assertEqual(subscription.product.amount_minor, 7_990)
        self.assertTrue(subscription.product.metadata["provider_price_snapshot_locked"])
        live_product = BillingProduct.objects.get(
            provider=PaymentProvider.APPLE_APP_STORE,
            environment=BillingProduct.Environment.LIVE,
            external_product_id="com.myscoope.basic.monthly",
        )
        self.assertTrue(live_product.active)
        self.assertEqual(live_product.amount_minor, 3_990)
        self.assertEqual(
            BillingProduct.objects.filter(
                provider=PaymentProvider.APPLE_APP_STORE,
                active=True,
            ).count(),
            8,
        )

    @staticmethod
    def _references():
        return tuple(
            AppleCatalogReference(
                offer_code=f"{plan}-{cadence}",
                product_id=f"com.myscoope.{plan}.{cadence}",
            )
            for plan in ("basic", "pro")
            for cadence in ("monthly", "annual")
        )
