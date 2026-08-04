from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from notas.application.services.food_imports.usda.foundation_foods_reader import (
    FoundationFoodsReaderError,
    read_foundation_food_payloads_from_json,
)
from notas.management.commands.dry_run_usda_food_payloads import (
    dry_run_usda_food_payloads,
)


class Command(BaseCommand):
    help = "Dry-run USDA Foundation Foods JSON import without writing to the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            type=str,
            help=(
                "Path to a JSON file containing USDA Foundation Foods payloads. "
                "Supports either a direct list or a FoundationFoods root object."
            ),
        )

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
            "--show-samples",
            action="store_true",
            help="Show sample rows for dry-run reasons such as mapping_failed or invalid rows.",
        )

        parser.add_argument(
            "--sample-size",
            type=int,
            default=5,
            help="Maximum number of samples to show per reason when --show-samples is used.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        source_version = options["source_version"]
        source_dataset = options["source_dataset"]
        show_samples = options["show_samples"]
        sample_size = options["sample_size"] if show_samples else 0

        if not path.exists():
            raise CommandError(f"File does not exist: {path}")

        if not path.is_file():
            raise CommandError(f"Path is not a file: {path}")

        try:
            payloads = read_foundation_food_payloads_from_json(path)
        except FoundationFoodsReaderError as exc:
            raise CommandError(str(exc)) from exc

        result = dry_run_usda_food_payloads(
            payloads=payloads,
            source_version=source_version,
            source_dataset=source_dataset,
            sample_size=sample_size,
        )

        self.stdout.write(self.style.SUCCESS("USDA dry-run completed."))

        self.stdout.write(f"total={result.total_rows}")
        self.stdout.write(f"valid={result.valid_rows}")
        self.stdout.write(f"invalid={result.invalid_rows}")
        self.stdout.write(f"duplicates={result.duplicate_rows}")
        self.stdout.write(f"failed={result.failed_rows}")
        self.stdout.write(f"would_import={result.would_import_rows}")
        self.stdout.write(f"would_skip={result.skipped_rows}")
        self.stdout.write(f"visibility_extended={result.extended_rows}")
        self.stdout.write(f"visibility_hidden={result.hidden_rows}")

        if result.reason_counts:
            self.stdout.write("reasons:")

            for reason, count in sorted(result.reason_counts.items()):
                self.stdout.write(f"- {reason}: {count}")

        if show_samples and result.issue_samples:
            self.stdout.write("samples:")

            for reason, samples in sorted(result.issue_samples.items()):
                self.stdout.write(f"- {reason}:")

                for sample in samples:
                    source_food_id = sample.source_food_id or "(none)"
                    description = sample.description or "(none)"

                    self.stdout.write(
                        "  "
                        f"index={sample.index} "
                        f"payload_type={sample.payload_type} "
                        f"source_food_id={source_food_id} "
                        f"description={description}"
                    )