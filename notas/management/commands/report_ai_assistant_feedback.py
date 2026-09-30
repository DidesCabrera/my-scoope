from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from notas.application.ai_intake.message_feedback import summarize_message_feedback


class Command(BaseCommand):
    help = "Report aggregate AI assistant message feedback without conversation content."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--output", default="")

    def handle(self, *args, **options):
        days = int(options["days"])
        if days < 1 or days > 365:
            raise CommandError("--days must be between 1 and 365")
        payload = summarize_message_feedback(days=days)
        serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        output = str(options.get("output") or "").strip()
        if output:
            try:
                with open(output, "w", encoding="utf-8") as handle:
                    handle.write(serialized + "\n")
            except OSError as exc:
                raise CommandError(f"Could not write feedback report: {exc}") from exc
            self.stdout.write(self.style.SUCCESS(f"Feedback report written to {output}"))
            return
        self.stdout.write(serialized)
