from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from notas.application.ai_intake.real_provider_validation import (
    built_in_real_provider_scenarios,
    get_validation_user,
    run_real_provider_validation,
)


class Command(BaseCommand):
    help = (
        "Run the controlled CM24 AI Assistant UX validation against the configured real provider. "
        "This command consumes provider usage and, when enabled, AI credits."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--live",
            action="store_true",
            help="Required explicit confirmation that real provider calls and credit usage are intended.",
        )
        user_group = parser.add_mutually_exclusive_group(required=False)
        user_group.add_argument("--user-id", type=int, default=None, help="Existing staging user id.")
        user_group.add_argument("--user-email", default="", help="Existing staging user email.")
        parser.add_argument(
            "--scenario",
            action="append",
            dest="scenarios",
            default=None,
            help="Scenario key to run. Repeat to select several. Defaults to all built-in scenarios.",
        )
        parser.add_argument(
            "--list-scenarios",
            action="store_true",
            help="List built-in CM24 validation scenarios without making provider calls.",
        )
        parser.add_argument(
            "--output",
            default="",
            help="Optional JSON report path. Parent directories are created automatically.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print the complete machine-readable report to stdout.",
        )
        parser.add_argument(
            "--fail-on-hard-regression",
            action="store_true",
            help="Return a non-zero command status when an automated hard invariant fails.",
        )

    def handle(self, *args, **options):
        if options["list_scenarios"]:
            for key, scenario in built_in_real_provider_scenarios().items():
                self.stdout.write(f"{key}: {scenario.description}")
            return

        if not options["live"]:
            raise CommandError(
                "CM24 validation makes real provider calls. Re-run with --live after reviewing the selected scenarios."
            )

        try:
            user = get_validation_user(
                user_id=options.get("user_id"),
                email=options.get("user_email") or "",
            )
            report = run_real_provider_validation(
                user=user,
                scenario_keys=options.get("scenarios"),
            )
        except Exception as exc:  # pragma: no cover - command boundary
            raise CommandError(str(exc)) from exc

        payload = report.as_dict()
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
        output_path = str(options.get("output") or "").strip()
        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(serialized + "\n", encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"CM24 report written: {path}"))

        if options["json"]:
            self.stdout.write(serialized)
        else:
            self._write_summary(report)

        if options["fail_on_hard_regression"] and not report.passed:
            raise CommandError(f"CM24 detected {len(report.hard_failures)} hard regression(s).")

    def _write_summary(self, report):
        marker = self.style.SUCCESS("AUTOMATED CHECKS PASSED") if report.passed else self.style.ERROR("HARD REGRESSION")
        self.stdout.write("AI Assistant CM24 real-provider UX validation")
        self.stdout.write(f"run_id: {report.run_id}")
        self.stdout.write(f"provider/model: {report.provider}/{report.model}")
        self.stdout.write(f"status: {marker}")
        self.stdout.write("")
        for scenario_result in report.scenarios:
            scenario_marker = "OK" if scenario_result.passed else "FAIL"
            self.stdout.write(f"[{scenario_marker}] {scenario_result.scenario.key}")
            for check in scenario_result.checks:
                check_marker = "OK" if check.passed else "FAIL"
                self.stdout.write(
                    f"  [{check_marker}] {check.key} ({check.severity}): {check.detail}"
                )
            self.stdout.write("  transcript:")
            for turn in scenario_result.turns:
                self.stdout.write(f"    USER: {turn.user_message}")
                self.stdout.write(f"    ASSISTANT: {turn.assistant_message}")
        self.stdout.write("")
        self.stdout.write(f"usage: {json.dumps(dict(report.usage_summary), ensure_ascii=False)}")
        self.stdout.write(f"credits: {json.dumps(dict(report.credit_summary), ensure_ascii=False)}")
        self.stdout.write("")
        self.stdout.write("Manual UX review is still required:")
        for prompt in report.manual_review_prompts:
            self.stdout.write(f"- {prompt}")
