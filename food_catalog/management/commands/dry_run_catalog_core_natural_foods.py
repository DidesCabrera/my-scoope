from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.core_natural_foods_seed import dry_run_core_natural_foods_seed


class Command(BaseCommand):
    help = "Dry-run the built-in core natural foods seed without writing database rows."

    def handle(self, *args, **options):
        result = dry_run_core_natural_foods_seed()

        self.stdout.write(self.style.SUCCESS("Food Catalog core natural foods dry-run completed."))
        self.stdout.write(f"total={result.total_rows}")
        self.stdout.write(f"valid={result.valid_rows}")
        self.stdout.write(f"invalid={result.invalid_rows}")
        self.stdout.write(f"to_create={result.to_create}")
        self.stdout.write(f"to_update={result.to_update}")

        if result.validation_errors:
            for error in result.validation_errors:
                self.stdout.write(f"- {error}")
            raise CommandError("Core natural foods seed is invalid.")
