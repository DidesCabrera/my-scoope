from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from accounts.seed_plans import seed_account_plans
from billing.application.services.catalog import (
    CatalogMappingError,
    PaddleCatalogReference,
    configure_paddle_catalog,
)
from billing.catalog import DEFAULT_BILLING_OFFERS, seed_billing_offers
from billing.models import BillingOffer, BillingProduct, PaymentProvider
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

        self.assertEqual(prices["basic"].monthly, "CLP 7.990")
        self.assertEqual(prices["basic"].annual, "CLP 79.900")
        self.assertEqual(prices["basic"].annual_monthly_equivalent, "CLP 6.658")
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
        self.assertEqual(basic.amount_minor, 7_990)

    def test_existing_paddle_price_cannot_be_rewritten_after_canonical_change(self):
        seed_billing_offers()
        references = self._paddle_references()
        configure_paddle_catalog(environment="sandbox", references=references)
        offer = BillingOffer.objects.get(code="basic-monthly")
        offer.amount_minor = 8_490
        offer.save(update_fields=["amount_minor", "updated_at"])

        with self.assertRaises(CatalogMappingError):
            configure_paddle_catalog(environment="sandbox", references=references)

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
