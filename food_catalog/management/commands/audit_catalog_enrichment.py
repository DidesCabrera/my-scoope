import json

from django.core.management.base import BaseCommand

from food_catalog.infrastructure.enrichment import audit_catalog_enrichment


class Command(BaseCommand):
    help = "Read-only audit of CatalogFood enrichment gaps in the connected database."

    def handle(self, *args, **options):
        audit = audit_catalog_enrichment()
        self.stdout.write(json.dumps({
            "total": audit.total,
            "missing_counts": audit.missing_counts,
            "client_requirement_gaps": audit.client_requirement_gaps,
        }, ensure_ascii=False, indent=2, sort_keys=True))
