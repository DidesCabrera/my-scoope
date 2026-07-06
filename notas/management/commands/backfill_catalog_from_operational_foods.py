from django.core.management.base import BaseCommand, CommandError

from food_catalog.models import CatalogFood
from notas.application.services.commands.food_catalog_backfill import (
    DEFAULT_OPERATIONAL_BACKFILL_SOURCE_VERSION,
    OPERATIONAL_BACKFILL_SOURCE_NAME,
    OperationalFoodCatalogBackfillError,
    backfill_catalog_from_operational_foods,
)


class Command(BaseCommand):
    help = "Backfill trusted notas.Food rows into Food Catalog master candidates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Compute the backfill plan without writing food_catalog rows.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional maximum number of eligible operational foods to inspect.",
        )
        parser.add_argument(
            "--source-name",
            default=OPERATIONAL_BACKFILL_SOURCE_NAME,
            help="CatalogFoodSource source_name used to trace this backfill.",
        )
        parser.add_argument(
            "--source-version",
            default=DEFAULT_OPERATIONAL_BACKFILL_SOURCE_VERSION,
            help="Source version label stored in CatalogImportBatch and CatalogFoodSource.",
        )
        parser.add_argument(
            "--status",
            default=CatalogFood.STATUS_REVIEWED,
            choices=[
                CatalogFood.STATUS_MANUAL_CANDIDATE,
                CatalogFood.STATUS_NORMALIZED,
                CatalogFood.STATUS_PENDING_REVIEW,
                CatalogFood.STATUS_REVIEWED,
                CatalogFood.STATUS_VERIFIED,
            ],
            help="Non-published curation status assigned to created CatalogFood rows.",
        )
        parser.add_argument(
            "--notes",
            default="",
            help="Optional notes stored in CatalogImportBatch when not using --dry-run.",
        )
        parser.add_argument(
            "--sample-size",
            type=int,
            default=0,
            help="Optional number of skipped/failed samples to include in stdout per reason.",
        )

    def handle(self, *args, **options):
        try:
            result = backfill_catalog_from_operational_foods(
                dry_run=options["dry_run"],
                limit=options["limit"],
                source_name=options["source_name"],
                source_version=options["source_version"],
                status=options["status"],
                notes=options["notes"],
                sample_size=options["sample_size"],
            )
        except OperationalFoodCatalogBackfillError as exc:
            raise CommandError(str(exc)) from exc

        prefix = "DRY RUN: " if result.dry_run else ""
        batch_info = ""
        if result.batch is not None:
            batch_info = f", batch_id={result.batch.id}, status={result.batch.status}"

        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Operational food catalog backfill completed: "
                f"total={result.total_rows}, "
                f"created={result.created_rows}, "
                f"skipped={result.skipped_rows}, "
                f"failed={result.failed_rows}"
                f"{batch_info}"
            )
        )

        if result.reason_counts:
            self.stdout.write("Reason counts:")
            for reason, count in sorted(result.reason_counts.items()):
                self.stdout.write(f"  {reason}: {count}")

        if result.samples:
            self.stdout.write("Samples:")
            for reason, samples in sorted(result.samples.items()):
                for sample in samples:
                    self.stdout.write(
                        f"  {reason}: food_id={sample.food_id}, name={sample.name}"
                    )
