from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from accounts.seed_plans import seed_account_plans
from billing.application.services.catalog import (
    AppleCatalogReference,
    CatalogMappingError,
    GooglePlayCatalogReference,
    PaddleCatalogReference,
    configure_apple_catalog,
    configure_google_play_catalog,
    configure_paddle_catalog,
)
from billing.catalog import DEFAULT_BILLING_OFFERS, seed_billing_offers, seed_credit_pack_offers
from billing.models import BillingOffer, BillingProduct, CreditPackOffer, PaymentProvider, ProviderSubscription
from billing.presentation.public_catalog import build_public_plan_prices


class CommercialCatalogTests(TestCase):
    def setUp(self):
        seed_account_plans()

    def test_seed_creates_the_four_canonical_paid_offers(self):
        summary = seed_billing_offers()

        self.assertEqual(summary["created"], len(DEFAULT_BILLING_OFFERS))
        self.assertEqual(
            set(BillingOffer.objects.values_list("code", flat=True)),
            {"basic-monthly", "basic-annual", "pro-monthly", "pro-annual"},
        )

    def test_credit_pack_seed_detects_price_drift_without_overwriting(self):
        self.assertEqual(seed_credit_pack_offers()["unchanged"], 3)
        offer = CreditPackOffer.objects.get(code="credits-500")
        offer.amount_minor = 1
        offer.save(update_fields=["amount_minor", "updated_at"])
        self.assertEqual(seed_credit_pack_offers()["drifted"], 1)
        offer.refresh_from_db()
        self.assertEqual(offer.amount_minor, 1)

    def test_seed_never_overwrites_a_changed_price(self):
        seed_billing_offers()
        offer = BillingOffer.objects.get(code="basic-monthly")
        offer.amount_minor = 8_490
        offer.save(update_fields=["amount_minor", "updated_at"])

        summary = seed_billing_offers()

        offer.refresh_from_db()
        self.assertEqual(summary["drifted"], 1)
        self.assertEqual(offer.amount_minor, 8_490)

    def test_public_prices_are_derived_from_canonical_offers(self):
        seed_billing_offers()
        prices = build_public_plan_prices()

        self.assertEqual(prices["basic"].monthly, "CLP 3.990")
        self.assertEqual(prices["basic"].annual, "CLP 34.990")
        self.assertEqual(prices["basic"].annual_monthly_equivalent, "CLP 2.916")
        self.assertTrue(prices["pro"].available)

    def test_catalog_command_is_idempotent(self):
        output = StringIO()
        call_command("seed_billing_catalog", stdout=output)

        second_output = StringIO()
        call_command("seed_billing_catalog", stdout=second_output)

        self.assertEqual(BillingOffer.objects.count(), 4)
        self.assertIn("unchanged", second_output.getvalue())

    def test_catalog_command_dry_run_does_not_create_offers(self):
        output = StringIO()

        call_command("seed_billing_catalog", "--dry-run", stdout=output)

        self.assertEqual(BillingOffer.objects.count(), 0)
        self.assertIn("would seed", output.getvalue())

    def test_paddle_mapping_snapshots_canonical_prices_and_is_idempotent(self):
        seed_billing_offers()
        references = self._paddle_references()

        first = configure_paddle_catalog(environment="sandbox", references=references)
        second = configure_paddle_catalog(environment="sandbox", references=references)

        self.assertEqual(first, {"created": 4, "reused": 0, "replaced": 0})
        self.assertEqual(second, {"created": 0, "reused": 4, "replaced": 0})
        basic = BillingProduct.objects.get(external_price_id="pri_basic_monthly")
        self.assertEqual(basic.provider, PaymentProvider.PADDLE)
        self.assertEqual(basic.environment, BillingProduct.Environment.SANDBOX)
        self.assertEqual(basic.amount_minor, 3_990)

    def test_existing_paddle_price_cannot_be_rewritten_after_canonical_change(self):
        seed_billing_offers()
        references = self._paddle_references()
        configure_paddle_catalog(environment="sandbox", references=references)
        offer = BillingOffer.objects.get(code="basic-monthly")
        offer.amount_minor = 8_490
        offer.save(update_fields=["amount_minor", "updated_at"])

        with self.assertRaises(CatalogMappingError):
            configure_paddle_catalog(environment="sandbox", references=references)

    def test_apple_mapping_snapshots_canonical_prices_and_is_idempotent(self):
        seed_billing_offers()
        references = self._apple_references()

        first = configure_apple_catalog(environment="live", references=references)
        second = configure_apple_catalog(environment="live", references=references)

        self.assertEqual(first, {"created": 4, "reused": 0, "replaced": 0})
        self.assertEqual(second, {"created": 0, "reused": 4, "replaced": 0})
        basic = BillingProduct.objects.get(external_product_id="com.myscoope.basic.monthly")
        self.assertEqual(basic.provider, PaymentProvider.APPLE_APP_STORE)
        self.assertEqual(basic.environment, BillingProduct.Environment.LIVE)
        self.assertEqual(basic.amount_minor, 3_990)
        self.assertEqual(basic.external_price_id, "")

    def test_apple_product_cannot_be_reassigned_to_another_offer(self):
        seed_billing_offers()
        configure_apple_catalog(environment="live", references=self._apple_references())
        conflicting = (
            AppleCatalogReference(
                offer_code="pro-monthly",
                product_id="com.myscoope.basic.monthly",
            ),
        )

        with self.assertRaises(CatalogMappingError):
            configure_apple_catalog(environment="live", references=conflicting)

    def test_unused_apple_product_can_keep_its_id_after_prelaunch_reprice(self):
        seed_billing_offers()
        offer = BillingOffer.objects.get(code="basic-monthly")
        offer.amount_minor = 7_990
        offer.save(update_fields=["amount_minor", "updated_at"])
        configure_apple_catalog(environment="sandbox", references=self._apple_references())
        product = BillingProduct.objects.get(provider=PaymentProvider.APPLE_APP_STORE, offer=offer)
        product.active = False
        product.save(update_fields=["active", "updated_at"])
        offer.amount_minor = 3_990
        offer.save(update_fields=["amount_minor", "updated_at"])

        summary = configure_apple_catalog(environment="sandbox", references=self._apple_references())

        product.refresh_from_db()
        self.assertEqual(summary, {"created": 0, "reused": 4, "replaced": 1})
        self.assertTrue(product.active)
        self.assertEqual(product.amount_minor, 3_990)
        self.assertEqual(product.metadata["prelaunch_price_history"][0]["amount_minor"], 7_990)
        self.assertEqual(BillingProduct.objects.filter(provider=PaymentProvider.APPLE_APP_STORE).count(), 4)

    def test_apple_product_with_subscription_history_preserves_provider_price_snapshot(self):
        seed_billing_offers()
        offer = BillingOffer.objects.get(code="basic-monthly")
        offer.amount_minor = 7_990
        offer.save(update_fields=["amount_minor", "updated_at"])
        configure_apple_catalog(environment="sandbox", references=self._apple_references())
        product = BillingProduct.objects.get(provider=PaymentProvider.APPLE_APP_STORE, offer=offer)
        user = get_user_model().objects.create_user(username="mobile_price_history", password="unused")
        ProviderSubscription.objects.create(
            user=user, product=product, provider=PaymentProvider.APPLE_APP_STORE,
            external_subscription_id="apple_existing_contract",
        )
        product.active = False
        product.save(update_fields=["active", "updated_at"])
        offer.amount_minor = 3_990
        offer.save(update_fields=["amount_minor", "updated_at"])

        summary = configure_apple_catalog(environment="sandbox", references=self._apple_references())

        product.refresh_from_db()
        self.assertEqual(summary, {"created": 0, "reused": 4, "replaced": 0})
        self.assertTrue(product.active)
        self.assertEqual(product.amount_minor, 7_990)
        self.assertTrue(product.metadata["provider_price_snapshot_locked"])
        product.full_clean()

    def test_google_base_plan_ids_are_scoped_to_each_existing_subscription(self):
        seed_billing_offers()
        references = self._google_references()

        first = configure_google_play_catalog(environment="sandbox", references=references)
        second = configure_google_play_catalog(environment="sandbox", references=references)

        self.assertEqual(first, {"created": 4, "reused": 0, "replaced": 0})
        self.assertEqual(second, {"created": 0, "reused": 4, "replaced": 0})
        self.assertEqual(BillingProduct.objects.filter(provider=PaymentProvider.GOOGLE_PLAY).count(), 4)
        self.assertEqual(
            BillingProduct.objects.filter(provider=PaymentProvider.GOOGLE_PLAY, external_price_id="monthly").count(), 2
        )

    def test_unused_google_base_plan_can_keep_its_id_after_prelaunch_reprice(self):
        seed_billing_offers()
        offer = BillingOffer.objects.get(code="basic-monthly")
        offer.amount_minor = 7_990
        offer.save(update_fields=["amount_minor", "updated_at"])
        configure_google_play_catalog(environment="sandbox", references=self._google_references())
        product = BillingProduct.objects.get(provider=PaymentProvider.GOOGLE_PLAY, offer=offer)
        product.active = False
        product.save(update_fields=["active", "updated_at"])
        offer.amount_minor = 3_990
        offer.save(update_fields=["amount_minor", "updated_at"])

        summary = configure_google_play_catalog(environment="sandbox", references=self._google_references())

        product.refresh_from_db()
        self.assertEqual(summary, {"created": 0, "reused": 4, "replaced": 1})
        self.assertEqual(product.amount_minor, 3_990)
        self.assertEqual(product.metadata["prelaunch_price_history"][0]["amount_minor"], 7_990)

    def test_active_provider_mapping_must_match_its_canonical_offer(self):
        seed_billing_offers()
        offer = BillingOffer.objects.get(code="basic-monthly")
        mapping = BillingProduct(
            provider=PaymentProvider.PADDLE,
            environment=BillingProduct.Environment.SANDBOX,
            external_product_id="pro_basic",
            external_price_id="pri_basic_wrong",
            offer=offer,
            account_plan=offer.account_plan,
            amount_minor=1,
            currency=offer.currency,
            interval=offer.interval,
        )

        with self.assertRaises(ValidationError):
            mapping.full_clean()

    @staticmethod
    def _paddle_references():
        return tuple(
            PaddleCatalogReference(
                offer_code=f"{plan}-{cadence}",
                product_id=f"pro_{plan}",
                price_id=f"pri_{plan}_{cadence}",
            )
            for plan in ("basic", "pro")
            for cadence in ("monthly", "annual")
        )

    @staticmethod
    def _apple_references():
        return tuple(
            AppleCatalogReference(
                offer_code=f"{plan}-{cadence}",
                product_id=f"com.myscoope.{plan}.{cadence}",
            )
            for plan in ("basic", "pro")
            for cadence in ("monthly", "annual")
        )

    @staticmethod
    def _google_references():
        return tuple(
            GooglePlayCatalogReference(
                offer_code=f"{plan}-{cadence}",
                product_id=f"myscoope_{plan}",
                base_plan_id=cadence,
            )
            for plan in ("basic", "pro")
            for cadence in ("monthly", "annual")
        )
