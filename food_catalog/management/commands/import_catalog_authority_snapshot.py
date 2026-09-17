import os

import requests
from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.releases import (
    CatalogReleaseError,
    import_authority_snapshot,
)


class Command(BaseCommand):
    help = "Bootstrap an empty catalog authority from one protected master snapshot."

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True)
        parser.add_argument("--token", default="")

    def handle(self, *args, **options):
        token = str(options["token"] or "").strip() or os.environ.get(
            "FOOD_CATALOG_RELEASE_TOKEN",
            "",
        ).strip()
        if not token:
            raise CommandError("FOOD_CATALOG_RELEASE_TOKEN is required.")
        try:
            response = requests.get(
                options["url"],
                headers={"Authorization": f"Bearer {token}"},
                timeout=60,
            )
            response.raise_for_status()
            count = import_authority_snapshot(response.json())
        except (requests.RequestException, ValueError, CatalogReleaseError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Authority bootstrap imported {count} foods."))
