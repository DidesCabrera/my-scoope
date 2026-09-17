from django.core.management.base import BaseCommand, CommandError

from billing.application.services.catalog import (
    CatalogMappingError,
    GooglePlayCatalogReference,
    configure_google_play_catalog,
)
from billing.models import BillingProduct


class Command(BaseCommand):
    help = "Map canonical My Scoope offers to Google Play subscription base plans."

    def add_arguments(self, parser):
        parser.add_argument("--environment", choices=BillingProduct.Environment.values, required=True)
        for plan in ("basic", "pro"):
            parser.add_argument(f"--{plan}-product-id", required=True)
            parser.add_argument(f"--{plan}-monthly-base-plan-id", default="monthly")
            parser.add_argument(f"--{plan}-annual-base-plan-id", default="annual")

    def handle(self, *args, **options):
        references = tuple(
            GooglePlayCatalogReference(
                offer_code=f"{plan}-{cadence}",
                product_id=options[f"{plan}_product_id"],
                base_plan_id=options[f"{plan}_{cadence}_base_plan_id"],
            )
            for plan in ("basic", "pro")
            for cadence in ("monthly", "annual")
        )
        try:
            summary = configure_google_play_catalog(environment=options["environment"], references=references)
        except CatalogMappingError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Google Play catalog mapped: {summary}"))
