"""Import brand-submitted foods into Food Catalog curation intake."""

from django.core.management.base import BaseCommand, CommandError

from food_catalog.application.brand_intake import (
    apply_brand_food_intake_csv,
    brand_food_intake_identity,
    dry_run_brand_food_intake_csv,
)
from food_catalog.infrastructure.imports.governance import record_catalog_import_dry_run
from food_catalog.models import CatalogImportBatch


class Command(BaseCommand):
    help = "Import brand-submitted food rows as Food Catalog curation records."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the brand intake CSV file.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the CSV without writing CatalogFood records.",
        )
        parser.add_argument("--limit", type=int, required=True, help="Initial brand sample size (1-5).")
        parser.add_argument("--reason", required=True)
        parser.add_argument("--dry-run-batch-id", type=int)

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        if options["limit"] < 1 or options["limit"] > 500:
            raise CommandError("Brand batch limit must be between 1 and 500; applies above 5 require FCG09 approval.")
        if options["dry_run"]:
            result = dry_run_brand_food_intake_csv(csv_path, limit=options["limit"])
            batch = record_catalog_import_dry_run(
                identity=brand_food_intake_identity(csv_path, limit=options["limit"]),
                total_rows=result.total_rows,
                would_import_rows=result.total_rows - result.skipped_rows,
                skipped_rows=result.skipped_rows,
                failed_rows=0,
                reason=options["reason"],
                summary_payload={"errors": result.errors},
            )
        else:
            if not options["dry_run_batch_id"]:
                raise CommandError("--dry-run-batch-id is required for apply.")
            try:
                dry_run_batch = CatalogImportBatch.objects.get(pk=options["dry_run_batch_id"])
            except CatalogImportBatch.DoesNotExist as exc:
                raise CommandError(str(exc)) from exc
            result = apply_brand_food_intake_csv(
                csv_path,
                dry_run_batch=dry_run_batch,
                reason=options["reason"],
                limit=options["limit"],
            )

        for error in result.errors:
            self.stderr.write(self.style.ERROR(error))

        self.stdout.write(
            "Brand intake: "
            f"total={result.total_rows} created={result.created_rows} "
            f"updated={result.updated_rows} skipped={result.skipped_rows}"
        )

        if result.errors:
            raise CommandError("Brand intake CSV contains invalid rows.")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Dry run OK. No catalog records were written. dry_run_batch_id={batch.pk}"))
        else:
            self.stdout.write(self.style.SUCCESS("Brand intake imported."))
