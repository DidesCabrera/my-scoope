from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.enrichment import CatalogEnrichmentError, revert_enrichment_batch
from food_catalog.models import CatalogEnrichmentBatch


class Command(BaseCommand):
    help = "Safely compensate an applied enrichment batch when its fields have not changed again."

    def add_arguments(self, parser):
        parser.add_argument("batch_ref")
        parser.add_argument("--reason", required=True)
        parser.add_argument("--confirm-revert", action="store_true")

    def handle(self, *args, **options):
        if not options["confirm_revert"]:
            raise CommandError("--confirm-revert is required")
        try:
            batch = CatalogEnrichmentBatch.objects.get(batch_ref=options["batch_ref"])
            revert_enrichment_batch(batch=batch, reason=options["reason"])
        except (CatalogEnrichmentBatch.DoesNotExist, CatalogEnrichmentError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"Reverted batch {batch.batch_ref} with append-only compensating events.")
