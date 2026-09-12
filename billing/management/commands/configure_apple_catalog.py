from django.core.management.base import BaseCommand, CommandError

from billing.application.services.catalog import (
    AppleCatalogReference,
    CatalogMappingError,
    configure_apple_catalog,
)
from billing.models import BillingProduct


class Command(BaseCommand):
    help = "Map canonical My Scoope offers to existing App Store Connect product identifiers."

    def add_arguments(self, parser):
        parser.add_argument("--environment", choices=BillingProduct.Environment.values, required=True)
        for plan in ("basic", "pro"):
            parser.add_argument(f"--{plan}-monthly-product-id", required=True)
            parser.add_argument(f"--{plan}-annual-product-id", required=True)

    def handle(self, *args, **options):
        references = tuple(
            AppleCatalogReference(
                offer_code=f"{plan}-{cadence}",
                product_id=options[f"{plan}_{cadence}_product_id"],
            )
            for plan in ("basic", "pro")
            for cadence in ("monthly", "annual")
        )
        try:
            summary = configure_apple_catalog(
                environment=options["environment"],
                references=references,
            )
        except CatalogMappingError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Apple catalog mapped: {summary}"))
