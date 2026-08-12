import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.enrichment import CatalogEnrichmentError, dry_run_enrichment_manifest
from food_catalog.models import CatalogEnrichmentBatch


class Command(BaseCommand):
    help = "Validate and persist field proposals without modifying CatalogFood."

    def add_arguments(self, parser):
        parser.add_argument("manifest")

    def handle(self, *args, **options):
        try:
            manifest = json.loads(Path(options["manifest"]).read_text(encoding="utf-8"))
            batch = CatalogEnrichmentBatch.objects.get(batch_ref=manifest.get("batch_ref"))
            result = dry_run_enrichment_manifest(batch=batch, manifest=manifest)
        except (OSError, json.JSONDecodeError, CatalogEnrichmentBatch.DoesNotExist, CatalogEnrichmentError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps({"batch_ref": str(batch.batch_ref), "status": batch.status,
                                      "total": result.total, "valid": result.valid, "invalid": result.invalid}))
