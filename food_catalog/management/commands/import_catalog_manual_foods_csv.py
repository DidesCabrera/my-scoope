from django.core.management.base import BaseCommand, CommandError

from food_catalog.application.manual_intake import (
    apply_manual_evidence_csv,
    dry_run_manual_evidence_csv,
    manual_evidence_identity,
)
from food_catalog.infrastructure.imports.governance import record_catalog_import_dry_run
from food_catalog.models import CatalogImportBatch


class Command(BaseCommand):
    help = "Dry-run or import manually curated foods with explicit evidence."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, required=True)
        parser.add_argument("--reason", required=True)
        parser.add_argument("--dry-run-batch-id", type=int)

    def handle(self, *args, **options):
        if options["limit"] < 1 or options["limit"] > 500:
            raise CommandError("Manual batch limit must be between 1 and 500; applies above 5 require FCG09 approval.")
        plan = dry_run_manual_evidence_csv(options["csv_path"], limit=options["limit"])
        versions = {row.source_version for row in plan.rows}
        if len(versions) > 1:
            raise CommandError("All rows must share one source_version.")
        source_version = next(iter(versions), "invalid")
        if options["dry_run"]:
            batch = record_catalog_import_dry_run(
                identity=manual_evidence_identity(options["csv_path"], limit=options["limit"], source_version=source_version),
                total_rows=plan.total_rows,
                would_import_rows=plan.valid_rows,
                skipped_rows=plan.invalid_rows,
                failed_rows=0,
                reason=options["reason"],
                summary_payload={"errors": plan.errors},
            )
            self.stdout.write(f"Manual dry-run: total={plan.total_rows} valid={plan.valid_rows} invalid={plan.invalid_rows} dry_run_batch_id={batch.pk}")
            if plan.errors:
                raise CommandError("Manual evidence CSV contains invalid rows.")
            return
        if not options["dry_run_batch_id"]:
            raise CommandError("--dry-run-batch-id is required for apply.")
        try:
            dry_run = CatalogImportBatch.objects.get(pk=options["dry_run_batch_id"])
            result = apply_manual_evidence_csv(
                options["csv_path"], limit=options["limit"], dry_run_batch=dry_run, reason=options["reason"]
            )
        except (CatalogImportBatch.DoesNotExist, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"Manual intake batch_id={result.batch.pk} total={result.total_rows} created={result.created_rows} updated={result.updated_rows} published=0"
        ))
