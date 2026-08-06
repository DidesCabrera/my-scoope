import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from mobile_api.api import api

DEFAULT_OUTPUT = Path(settings.BASE_DIR) / "docs/00_current/api/mobile-v1.openapi.json"


class Command(BaseCommand):
    help = "Export or verify the committed OpenAPI contract for the consumer mobile API."

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true")
        parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)

    def handle(self, *args, **options):
        output = options["output"]
        schema = api.get_openapi_schema(path_prefix="/api/v1/")
        serialized = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

        if options["check"]:
            if not output.exists():
                raise CommandError(f"Committed OpenAPI contract is missing: {output}")
            if output.read_text(encoding="utf-8") != serialized:
                raise CommandError(
                    "Committed mobile OpenAPI contract is stale. "
                    "Run `python manage.py export_mobile_openapi`."
                )
            self.stdout.write(self.style.SUCCESS("Mobile OpenAPI contract is current."))
            return

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Mobile OpenAPI contract exported to {output}"))
