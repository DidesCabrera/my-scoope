from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.core_natural_foods_seed import apply_core_natural_foods_seed


class Command(BaseCommand):
    help = "Apply the built-in core natural foods seed to Food Catalog."

    def add_arguments(self, parser):
        parser.add_argument(
            "--publish",
            action="store_true",
            help=(
                "Publish seeded foods after creation/update. Publication still passes "
                "through the protected Food Catalog workflow."
            ),
        )

    def handle(self, *args, **options):
        try:
            result = apply_core_natural_foods_seed(publish=options["publish"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Food Catalog core natural foods seed applied: "
                f"total={result.total_rows}, "
                f"created={result.created_rows}, "
                f"updated={result.updated_rows}, "
                f"published={result.published_rows}"
            )
        )

        if result.blocked_publications:
            self.stdout.write("blocked_publications:")
            for blocked in result.blocked_publications:
                self.stdout.write(f"- {blocked}")
