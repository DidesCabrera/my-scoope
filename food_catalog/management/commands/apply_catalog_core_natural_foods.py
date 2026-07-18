from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.core_natural_foods_seed import apply_core_natural_foods_seed
from food_catalog.models import CatalogImportBatch


class Command(BaseCommand):
    help = "Apply the built-in core natural foods seed to Food Catalog."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run-batch-id", type=int, required=True)
        parser.add_argument("--reason", required=True)

    def handle(self, *args, **options):
        try:
            dry_run_batch = CatalogImportBatch.objects.get(pk=options["dry_run_batch_id"])
            result = apply_core_natural_foods_seed(
                dry_run_batch=dry_run_batch,
                reason=options["reason"],
            )
        except (ValueError, CatalogImportBatch.DoesNotExist) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Food Catalog core natural foods seed applied: "
                f"total={result.total_rows}, "
                f"created={result.created_rows}, "
                f"updated={result.updated_rows}, "
                f"published=0, batch_id={result.batch.pk}"
            )
        )
