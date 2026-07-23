import json

from django.core.management.base import BaseCommand, CommandError

from core.ai_project_context import build_ai_project_context


class Command(BaseCommand):
    help = "Emit compact sanitized project context for AI clients and focused exports."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--domain", default="")
        parser.add_argument("--decision-limit", type=int, default=12)
        parser.add_argument("--skip-database", action="store_true")

    def handle(self, *args, **options):
        decision_limit = options["decision_limit"]
        if not 1 <= decision_limit <= 50:
            raise CommandError("--decision-limit must be between 1 and 50.")
        payload = build_ai_project_context(
            domain=options["domain"].strip(),
            include_database=not options["skip_database"],
            decision_limit=decision_limit,
        )
        if options["as_json"]:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            return
        self.stdout.write(
            f"My Scoope AI project context · status={payload['project_status']['status']} · "
            f"cycles={len(payload['live_cycles'])} · decisions={len(payload['decisions'])}"
        )
        self.stdout.write("AI is a current project client. Context informs judgment; it is not a fixed script.")
        for cycle in payload["live_cycles"]:
            self.stdout.write(f"[{cycle['status_class'].upper()}] {cycle['title']}")

