import json

from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.readiness_pipeline import prepare_readiness_batch, readiness_incomplete_queryset
from food_catalog.models import CatalogFood


class Command(BaseCommand):
    help = "Generate and dry-run a compact readiness batch without publishing or snapshotting."

    def add_arguments(self, parser):
        parser.add_argument("--environment", required=True, choices=("staging", "production"))
        parser.add_argument("--reason", required=True)
        parser.add_argument("--ids", default="", help="Optional comma-separated CatalogFood IDs.")
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--after-id", type=int, default=0, help="Resume with foods after this CatalogFood ID.")

    def handle(self, *args, **options):
        if not 1 <= options["limit"] <= 10:
            raise CommandError("--limit must be between 1 and 10")
        queryset = readiness_incomplete_queryset()
        if options["ids"]:
            try:
                ids = {int(value.strip()) for value in options["ids"].split(",") if value.strip()}
            except ValueError as exc:
                raise CommandError("--ids must contain integers") from exc
            queryset = queryset.filter(pk__in=ids)
        queryset = queryset.filter(
            pk__gt=options["after_id"],
            status__in=(CatalogFood.STATUS_MANUAL_CANDIDATE, CatalogFood.STATUS_PENDING_REVIEW),
        ).order_by("id")
        foods = list(queryset[:options["limit"]])
        selected_ids = [food.pk for food in foods]
        remaining = queryset.exclude(pk__in=selected_ids).count()
        next_after_id = selected_ids[-1] if remaining and selected_ids else None
        try:
            batch, result, skipped = prepare_readiness_batch(
                foods=foods, environment=options["environment"], reason=options["reason"]
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps({
            "batch_ref": str(batch.batch_ref), "status": batch.status,
            "total_proposals": result.total, "valid_proposals": result.valid,
            "invalid_proposals": result.invalid, "skipped": skipped,
            "manifest_sha256": batch.manifest_sha256,
            "selected_food_ids": selected_ids,
            "remaining": remaining,
            "next_after_id": next_after_id,
        }, ensure_ascii=False, sort_keys=True))
