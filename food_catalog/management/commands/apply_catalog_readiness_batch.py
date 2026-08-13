from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.enrichment import CatalogEnrichmentError, apply_enrichment_batch
from food_catalog.models import CatalogEnrichmentBatch


class Command(BaseCommand):
    help = "Apply the exact stored readiness manifest after a valid dry-run."

    def add_arguments(self, parser):
        parser.add_argument("batch_ref")
        parser.add_argument("--reason", required=True)
        parser.add_argument("--confirm-apply", action="store_true")

    def handle(self, *args, **options):
        if not options["confirm_apply"]:
            raise CommandError("--confirm-apply is required")
        try:
            batch = CatalogEnrichmentBatch.objects.get(batch_ref=options["batch_ref"])
            apply_enrichment_batch(
                batch=batch, manifest=batch.manifest_payload, reason=options["reason"]
            )
        except (CatalogEnrichmentBatch.DoesNotExist, CatalogEnrichmentError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            f"Applied readiness batch {batch.batch_ref}: {batch.applied_proposals} changes; "
            "0 publications; 0 snapshots."
        )
