import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.enrichment import CatalogEnrichmentError, apply_enrichment_batch
from food_catalog.models import CatalogEnrichmentBatch


class Command(BaseCommand):
    help = "Apply the exact valid enrichment manifest; does not publish or snapshot."

    def add_arguments(self, parser):
        parser.add_argument("manifest")
        parser.add_argument("--reason", required=True)
        parser.add_argument("--confirm-apply", action="store_true")

    def handle(self, *args, **options):
        if not options["confirm_apply"]:
            raise CommandError("--confirm-apply is required")
        try:
            manifest = json.loads(Path(options["manifest"]).read_text(encoding="utf-8"))
            batch = CatalogEnrichmentBatch.objects.get(batch_ref=manifest.get("batch_ref"))
            apply_enrichment_batch(batch=batch, manifest=manifest, reason=options["reason"])
        except (OSError, json.JSONDecodeError, CatalogEnrichmentBatch.DoesNotExist, CatalogEnrichmentError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"Applied batch {batch.batch_ref}: {batch.applied_proposals} field changes; 0 publications; 0 snapshots.")
