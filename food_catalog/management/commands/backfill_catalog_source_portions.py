import json

from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.source_portion_backfill import backfill_source_portions


class Command(BaseCommand):
    help = "Dry-run or apply a bounded, resumable backfill of historical USDA household portions."

    def add_arguments(self, parser):
        parser.add_argument("--ids", default="", help="Optional comma-separated CatalogFood IDs.")
        parser.add_argument("--after-id", type=int, default=0, help="Resume after this CatalogFoodSource ID.")
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--reason", default="")

    def handle(self, *args, **options):
        try:
            ids = _parse_ids(options["ids"])
            result = backfill_source_portions(
                food_ids=ids,
                after_id=options["after_id"],
                limit=options["limit"],
                apply=options["apply"],
                reason=options["reason"],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps({
            "mode": "apply" if options["apply"] else "dry_run",
            "batch_ref": result.batch_ref,
            "proposed": result.proposed,
            "applied": result.applied,
            "remaining": result.remaining,
            "next_after_id": result.next_after_id,
            "rows": result.rows,
        }, ensure_ascii=False, sort_keys=True))


def _parse_ids(raw):
    if not raw:
        return None
    try:
        return {int(value.strip()) for value in raw.split(",") if value.strip()}
    except ValueError as exc:
        raise ValueError("ids must contain integers") from exc
