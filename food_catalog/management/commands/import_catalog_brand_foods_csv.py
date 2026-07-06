"""Import brand-submitted foods into Food Catalog curation intake."""

from django.core.management.base import BaseCommand, CommandError

from food_catalog.application.brand_intake import (
    apply_brand_food_intake_csv,
    dry_run_brand_food_intake_csv,
)


class Command(BaseCommand):
    help = "Import brand-submitted food rows as Food Catalog curation records."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the brand intake CSV file.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the CSV without writing CatalogFood records.",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        result = (
            dry_run_brand_food_intake_csv(csv_path)
            if options["dry_run"]
            else apply_brand_food_intake_csv(csv_path)
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
            self.stdout.write(self.style.SUCCESS("Dry run OK. No catalog records were written."))
        else:
            self.stdout.write(self.style.SUCCESS("Brand intake imported."))
