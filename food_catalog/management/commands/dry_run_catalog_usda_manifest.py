from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.imports.catalog_import import dry_run_catalog_food_import
from food_catalog.infrastructure.imports.governance import record_catalog_import_dry_run
from food_catalog.infrastructure.imports.usda_manifest_import import prepare_usda_manifest_import


class Command(BaseCommand):
    help = "Validate a mapped USDA manifest wave and record its governed dry-run."

    def add_arguments(self, parser):
        parser.add_argument("dataset_path")
        parser.add_argument("--manifest-path", required=True)
        parser.add_argument("--manifest-version", required=True)
        parser.add_argument("--expected-source", choices=["usda_foundation", "usda_sr_legacy"], required=True)
        parser.add_argument("--limit", type=int, required=True)
        parser.add_argument("--reason", required=True)

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
            result = dry_run_catalog_food_import(
                foods=prepared.selection.foods,
                source_name=prepared.identity.source_name,
                source_type=prepared.identity.source_type,
                sample_size=10,
            )
            batch = record_catalog_import_dry_run(
                identity=prepared.identity,
                total_rows=result.total_rows,
                would_import_rows=result.would_import_rows,
                skipped_rows=result.skipped_rows,
                failed_rows=result.failed_rows,
                reason=options["reason"],
                summary_payload={
                    "target_keys": [target.target_key for target in prepared.selection.targets],
                    "reason_counts": result.reason_counts,
                },
            )
        except (OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"USDA manifest dry-run #{batch.pk}: total={result.total_rows}, valid={result.valid_rows}, "
            f"importable={result.would_import_rows}, skipped={result.skipped_rows}, failed={result.failed_rows}"
        ))
