import json

from django.conf import settings
from django.core.management.base import BaseCommand

from notas.application.sharing.services import maintain_sharing_resources


class Command(BaseCommand):
    help = "Expire portable shares and delete old unclaimed revoked/expired resources."

    def add_arguments(self, parser):
        parser.add_argument(
            "--retention-days",
            type=int,
            default=getattr(settings, "SHARING_RESOURCE_RETENTION_DAYS", 30),
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        result = maintain_sharing_resources(
            retention_days=options["retention_days"],
            dry_run=dry_run,
        )
        result["dry_run"] = dry_run
        self.stdout.write(json.dumps(result, sort_keys=True))
