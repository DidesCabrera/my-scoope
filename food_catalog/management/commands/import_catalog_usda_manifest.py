from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.imports.catalog_import import import_catalog_food_batch
from food_catalog.infrastructure.imports.usda_manifest_import import prepare_usda_manifest_import
from food_catalog.models import CatalogImportBatch


class Command(BaseCommand):
    help = "Apply an explicitly mapped USDA manifest wave after an equivalent dry-run."

    def add_arguments(self, parser):
        parser.add_argument("dataset_path")
        parser.add_argument("--manifest-path", required=True)
        parser.add_argument("--manifest-version", required=True)
        parser.add_argument("--expected-source", choices=["usda_foundation", "usda_sr_legacy"], required=True)
        parser.add_argument("--limit", type=int, required=True)
        parser.add_argument("--dry-run-batch-id", type=int, required=True)
        parser.add_argument("--reason", required=True)
        parser.add_argument("--notes", default="")

    def handle(self, *args, **options):
        if not 1 <= options["limit"] <= 10:
            raise CommandError("The initial governed USDA manifest wave must contain 1-10 foods.")
        try:
            prepared = prepare_usda_manifest_import(
                dataset_path=options["dataset_path"],
                manifest_path=options["manifest_path"],
                manifest_version=options["manifest_version"],
                expected_source=options["expected_source"],
                limit=options["limit"],
            )
            dry_run_batch = CatalogImportBatch.objects.get(pk=options["dry_run_batch_id"])
            result = import_catalog_food_batch(
                foods=prepared.selection.foods,
                source_name=prepared.identity.source_name,
                source_version=prepared.identity.source_version,
                source_type=prepared.identity.source_type,
                notes=options["notes"],
                identity=prepared.identity,
                dry_run_batch=dry_run_batch,
                reason=options["reason"],
            )
        except (CatalogImportBatch.DoesNotExist, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"USDA manifest import #{result.batch.pk}: total={result.total_rows}, "
            f"imported={result.imported_rows}, skipped={result.skipped_rows}, failed={result.failed_rows}"
        ))
