from pathlib import Path
import hashlib

from django.core.management.base import BaseCommand, CommandError

from food_catalog.application.imports.usda.foundation_foods_reader import (
    FoundationFoodsReaderError,
    read_foundation_food_payloads_from_json,
)
from food_catalog.infrastructure.imports.catalog_import import CATALOG_SOURCE_NAME_USDA
from food_catalog.infrastructure.imports.usda_catalog_import import (
    dry_run_usda_catalog_food_payloads,
)
from food_catalog.infrastructure.imports.governance import (
    catalog_import_identity,
    record_catalog_import_dry_run,
)
from food_catalog.models import CatalogFood


class Command(BaseCommand):
    help = "Dry-run USDA JSON import into Food Catalog without writing database rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            type=str,
            help=(
                "Path to a JSON file containing USDA Foundation Foods payloads. "
                "Supports either a direct list or a FoundationFoods root object."
            ),
        )
        parser.add_argument("--limit", type=int, required=True, help="Initial sample size (1-10).")
        parser.add_argument("--reason", required=True)
        parser.add_argument(
            "--source-version",
            required=True,
            help="Source dataset version. Example: 2026-04.",
        )
        parser.add_argument(
            "--source-dataset",
            default="foundation_foods",
            help="Source dataset name. Example: foundation_foods.",
        )
        parser.add_argument(
            "--source-name",
            default=CATALOG_SOURCE_NAME_USDA,
            help="Human-readable source name checked against CatalogFoodSource.",
        )
        parser.add_argument(
            "--show-samples",
            action="store_true",
            help="Show sample rows for dry-run reasons such as invalid or duplicate rows.",
        )
        parser.add_argument(
            "--sample-size",
            type=int,
            default=5,
            help="Maximum number of samples to show per reason when --show-samples is used.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])

        if not path.exists():
            raise CommandError(f"File does not exist: {path}")

        if not path.is_file():
            raise CommandError(f"Path is not a file: {path}")

        try:
            payloads = read_foundation_food_payloads_from_json(path)
        except FoundationFoodsReaderError as exc:
            raise CommandError(str(exc)) from exc

        if options["limit"] < 1 or options["limit"] > 500:
            raise CommandError("USDA batch limit must be between 1 and 500; applies above 10 require FCG09 approval.")
        payloads = payloads[: options["limit"]]
        sample_size = options["sample_size"] if options["show_samples"] else 0
        result = dry_run_usda_catalog_food_payloads(
            payloads=payloads,
            source_version=options["source_version"],
            source_dataset=options["source_dataset"],
            source_name=options["source_name"],
            sample_size=sample_size,
        )
        identity = catalog_import_identity(
            source_type=CatalogFood.SOURCE_USDA,
            source_name=options["source_name"],
            source_version=options["source_version"],
            input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            parameters_payload={"source_dataset": options["source_dataset"], "limit": options["limit"]},
        )
        batch = record_catalog_import_dry_run(
            identity=identity,
            total_rows=result.total_rows,
            would_import_rows=result.would_import_rows,
            skipped_rows=result.skipped_rows,
            failed_rows=result.failed_rows,
            reason=options["reason"],
            summary_payload={"reason_counts": result.reason_counts, "invalid": result.invalid_rows, "duplicates": result.duplicate_rows},
        )

        self.stdout.write(self.style.SUCCESS("Food Catalog USDA dry-run completed."))
        self.stdout.write(f"total={result.total_rows}")
        self.stdout.write(f"valid={result.valid_rows}")
        self.stdout.write(f"invalid={result.invalid_rows}")
        self.stdout.write(f"duplicates={result.duplicate_rows}")
        self.stdout.write(f"failed={result.failed_rows}")
        self.stdout.write(f"would_import={result.would_import_rows}")
        self.stdout.write(f"would_skip={result.skipped_rows}")
        self.stdout.write(f"dry_run_batch_id={batch.pk}")

        if result.reason_counts:
            self.stdout.write("reasons:")
            for reason, count in sorted(result.reason_counts.items()):
                self.stdout.write(f"- {reason}: {count}")

        if options["show_samples"] and result.issue_samples:
            self.stdout.write("samples:")
            for reason, samples in sorted(result.issue_samples.items()):
                self.stdout.write(f"- {reason}:")
                for sample in samples:
                    source_food_id = sample.source_food_id or "(none)"
                    name = sample.name or "(none)"
                    self.stdout.write(
                        "  "
                        f"index={sample.index} "
                        f"source_food_id={source_food_id} "
                        f"name={name}"
                    )
