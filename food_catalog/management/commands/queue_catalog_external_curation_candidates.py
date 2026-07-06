from __future__ import annotations

from django.core.management.base import BaseCommand

from food_catalog.application.curation_candidates import (
    DEFAULT_MIN_SEEN_COUNT,
    DEFAULT_MIN_SELECTED_COUNT,
    queue_external_references_for_curation,
    should_queue_external_reference,
)
from food_catalog.models import ExternalFoodReference


class Command(BaseCommand):
    help = "Queue ExternalFoodReference rows as Food Catalog curation candidates."

    def add_arguments(self, parser):
        parser.add_argument("--min-selected-count", type=int, default=DEFAULT_MIN_SELECTED_COUNT)
        parser.add_argument("--min-seen-count", type=int, default=DEFAULT_MIN_SEEN_COUNT)
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show eligible references without creating or updating curation candidates.",
        )

    def handle(self, *args, **options):
        references = ExternalFoodReference.objects.filter(is_active=True).order_by(
            "-selected_count",
            "-seen_count",
            "display_name",
        )
        limit = options["limit"]
        if limit is not None:
            references = references[: max(0, limit)]

        min_selected_count = options["min_selected_count"]
        min_seen_count = options["min_seen_count"]

        if options["dry_run"]:
            eligible = [
                reference
                for reference in references
                if should_queue_external_reference(
                    reference,
                    min_selected_count=min_selected_count,
                    min_seen_count=min_seen_count,
                )
            ]
            self.stdout.write(self.style.SUCCESS(f"Eligible external references: {len(eligible)}"))
            for reference in eligible:
                self.stdout.write(
                    f"- [{reference.provider}:{reference.external_food_id}] {reference.display_name}"
                    + (f" · {reference.brand_name}" if reference.brand_name else "")
                    + f" · seen={reference.seen_count} selected={reference.selected_count}"
                )
            return

        result = queue_external_references_for_curation(
            references,
            min_selected_count=min_selected_count,
            min_seen_count=min_seen_count,
            limit=None,
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Queued external curation candidates: "
                f"created={result.created_count}, updated={result.updated_count}, skipped={result.skipped_count}"
            )
        )
