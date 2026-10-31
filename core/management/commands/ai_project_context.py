import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from core.ai_project_context import TASK_MODES, build_ai_project_context, build_ai_task_packet


class Command(BaseCommand):
    help = "Emit compact sanitized project context for AI clients and focused exports."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--domain", default="")
        parser.add_argument("--decision-limit", type=int)
        parser.add_argument("--skip-database", action="store_true")
        parser.add_argument(
            "--include-database",
            action="store_true",
            help="Include database-backed status in a compact packet.",
        )
        parser.add_argument(
            "--compact",
            action="store_true",
            help="Emit a task-scoped packet instead of the complete project context.",
        )
        parser.add_argument(
            "--task-mode",
            choices=tuple(TASK_MODES),
            default="consult",
            help="Select the workflow boundary used by the compact task packet.",
        )
        parser.add_argument(
            "--surface",
            default="",
            help="Optional user-facing surface or subsystem being changed.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        decision_limit = options["decision_limit"]
        if decision_limit is None:
            decision_limit = 5 if options["compact"] else 12
        if not 1 <= decision_limit <= 50:
            raise CommandError("--decision-limit must be between 1 and 50.")
        if options["skip_database"] and options["include_database"]:
            raise CommandError("Use only one of --skip-database or --include-database.")
        include_database = options["include_database"] or (
            not options["compact"] and not options["skip_database"]
        )
        builder = build_ai_task_packet if options["compact"] else build_ai_project_context
        builder_options: dict[str, Any] = {
            "domain": options["domain"].strip(),
            "include_database": include_database,
            "decision_limit": decision_limit,
        }
        if options["compact"]:
            builder_options.update(
                task_mode=options["task_mode"],
                surface=options["surface"].strip(),
            )
        payload = builder(**builder_options)
        if options["as_json"]:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            return
        if options["compact"]:
            self.stdout.write(
                f"My Scoope AI task packet · mode={payload['task']['mode']} · "
                f"domain={payload['task']['domain']} · decisions={len(payload['decisions'])}"
            )
            self.stdout.write(f"Validation: {payload['workflow']['validation']}")
            for cycle in payload["cycles"]["active"]:
                self.stdout.write(f"[ACTIVE] {cycle['title']}")
            return

        self.stdout.write(
            f"My Scoope AI project context · status={payload['project_status']['status']} · "
            f"active_cycles={len(payload['cycle_groups']['active'])} · "
            f"external_gates={len(payload['cycle_groups']['external_evidence_pending'])} · "
            f"decisions={len(payload['decisions'])}"
        )
        self.stdout.write("AI is a current project client. Context informs judgment; it is not a fixed script.")
        for cycle in payload["cycle_groups"]["active"]:
            self.stdout.write(f"[{cycle['status_class'].upper()}] {cycle['title']}")

