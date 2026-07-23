from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.core_natural_foods_seed import (
    core_natural_foods_seed_identity,
    dry_run_core_natural_foods_seed,
)
from food_catalog.infrastructure.imports.governance import record_catalog_import_dry_run


class Command(BaseCommand):
    help = "Dry-run the built-in core natural foods seed without writing database rows."

    def add_arguments(self, parser):
        parser.add_argument("--reason", required=True, help="Operational reason stored with the dry-run.")

    def handle(self, *args, **options):
        result = dry_run_core_natural_foods_seed()
        batch = record_catalog_import_dry_run(
            identity=core_natural_foods_seed_identity(),
            total_rows=result.total_rows,
            would_import_rows=result.to_create + result.to_update,
            skipped_rows=result.invalid_rows,
            failed_rows=0,
            reason=options["reason"],
            summary_payload={
                "valid": result.valid_rows,
                "invalid": result.invalid_rows,
                "to_create": result.to_create,
                "to_update": result.to_update,
            },
        )

        self.stdout.write(self.style.SUCCESS("Food Catalog core natural foods dry-run completed."))
        self.stdout.write(f"total={result.total_rows}")
        self.stdout.write(f"valid={result.valid_rows}")
        self.stdout.write(f"invalid={result.invalid_rows}")
        self.stdout.write(f"to_create={result.to_create}")
        self.stdout.write(f"to_update={result.to_update}")
        self.stdout.write(f"dry_run_batch_id={batch.pk}")

        if result.validation_errors:
            for error in result.validation_errors:
                self.stdout.write(f"- {error}")
            raise CommandError("Core natural foods seed is invalid.")
