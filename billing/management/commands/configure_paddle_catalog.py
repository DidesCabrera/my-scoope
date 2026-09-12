from django.core.management.base import BaseCommand, CommandError

from billing.application.services.catalog import (
    CatalogMappingError,
    PaddleCatalogReference,
    configure_paddle_catalog,
)
from billing.models import BillingProduct


class Command(BaseCommand):
    help = "Map canonical My Scoope offers to existing Paddle product and price IDs."

    def add_arguments(self, parser):
        parser.add_argument("--environment", choices=BillingProduct.Environment.values, required=True)
        for plan in ("basic", "pro"):
            parser.add_argument(f"--{plan}-product-id", required=True)
            parser.add_argument(f"--{plan}-monthly-price-id", required=True)
            parser.add_argument(f"--{plan}-annual-price-id", required=True)

    def handle(self, *args, **options):
        references = tuple(
            PaddleCatalogReference(
                offer_code=f"{plan}-{cadence}",
                product_id=options[f"{plan}_product_id"],
                price_id=options[f"{plan}_{cadence}_price_id"],
            )
            for plan in ("basic", "pro")
            for cadence in ("monthly", "annual")
        )
        try:
            summary = configure_paddle_catalog(
                environment=options["environment"],
                references=references,
            )
        except CatalogMappingError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Paddle catalog mapped: {summary}"))
