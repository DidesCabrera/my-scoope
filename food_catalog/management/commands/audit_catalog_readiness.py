import json

from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.readiness_audit import audit_catalog_readiness
from food_catalog.models import CatalogFood


class Command(BaseCommand):
    help = "Run the stable, read-only Food Catalog readiness audit."

    def add_arguments(self, parser):
        parser.add_argument("--ids", default="", help="Optional comma-separated CatalogFood IDs.")
        parser.add_argument("--include-foods", action="store_true")
        parser.add_argument("--fail-on-gaps", action="store_true")

    def handle(self, *args, **options):
        queryset = CatalogFood.objects.all()
        if options["ids"]:
            try:
                ids = {int(value.strip()) for value in options["ids"].split(",") if value.strip()}
            except ValueError as exc:
                raise CommandError("--ids must contain integers") from exc
            queryset = queryset.filter(pk__in=ids)
        audit = audit_catalog_readiness(queryset)
        self.stdout.write(json.dumps(
            audit.as_dict(include_foods=options["include_foods"]),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ))
        if options["fail_on_gaps"] and not audit.passes:
            raise CommandError("Food Catalog readiness audit found gaps.")
