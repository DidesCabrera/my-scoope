import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.document_registry import build_document_registry


class Command(BaseCommand):
    help = "List and validate active-cycle and decision document metadata."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--strict", action="store_true")

    def handle(self, *args, **options):
        registry = build_document_registry(Path(settings.BASE_DIR))
        payload = registry.as_dict()
        if options["as_json"]:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            self.stdout.write(
                f"Document registry: {len(registry.entries)} entries · "
                f"{len(registry.findings)} findings · valid={registry.valid}"
            )
            for key, value in sorted(payload["counts"].items()):
                self.stdout.write(f"  {key}: {value}")
            for finding in registry.findings:
                self.stdout.write(
                    f"[{finding.severity.upper()}] {finding.code} · {finding.path}: {finding.message}"
                )
        if options["strict"] and not registry.valid:
            raise CommandError("Document registry contains invalid metadata.")

