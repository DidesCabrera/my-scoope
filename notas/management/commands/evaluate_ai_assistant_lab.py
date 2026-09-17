from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from notas.application.ai_intake.evaluation_lab import (
    DEFAULT_LAB_SCENARIOS,
    run_evaluation_lab,
)
from notas.application.ai_intake.real_provider_validation import (
    built_in_real_provider_scenarios,
    get_validation_user,
)


class Command(BaseCommand):
    help = (
        "Evaluate the AI Assistant without the web UI. The default deterministic preflight "
        "reads real user data and runs the solver without provider calls. --live adds the "
        "configured real-model conversation and consumes provider usage/credits."
    )

    def add_arguments(self, parser):
        user_group = parser.add_mutually_exclusive_group(required=False)
        user_group.add_argument("--user-id", type=int, default=None, help="Existing user id.")
        user_group.add_argument("--user-email", default="", help="Existing user email.")
        parser.add_argument(
            "--live",
            action="store_true",
            help="Opt in to real provider calls after deterministic preflight passes.",
        )
        parser.add_argument(
            "--scenario",
            action="append",
            dest="scenarios",
            default=None,
            help="Scenario key to run. Repeat to select several.",
        )
        parser.add_argument(
            "--list-scenarios",
            action="store_true",
            help="List lab scenarios without reading user data or calling the provider.",
        )
        parser.add_argument(
            "--keep-artifacts",
            action="store_true",
            help="Keep reviewable proposals/actions created by a live lab run (default: clean them up).",
        )
        parser.add_argument("--output", default="", help="Optional JSON report path.")
        parser.add_argument("--json", action="store_true", help="Print the complete JSON report.")
        parser.add_argument(
            "--fail-on-regression",
            action="store_true",
            help="Return non-zero for fixture blockers or live hard regressions.",
        )

    def handle(self, *args, **options):
        if options["list_scenarios"]:
            catalog = built_in_real_provider_scenarios()
            for key in DEFAULT_LAB_SCENARIOS:
                scenario = catalog[key]
                capabilities = ", ".join(scenario.capability_ids) or "sin mapeo"
                self.stdout.write(f"{key} [{capabilities}]: {scenario.description}")
            return

        try:
            user = get_validation_user(
                user_id=options.get("user_id"),
                email=options.get("user_email") or "",
            )
            report = run_evaluation_lab(
                user=user,
                scenario_keys=options.get("scenarios"),
                live=bool(options.get("live")),
                cleanup_review_artifacts=not bool(options.get("keep_artifacts")),
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
            self.stdout.write(self.style.SUCCESS(f"Evaluation lab report written: {path}"))

        if options["json"]:
            self.stdout.write(serialized)
        else:
            self._write_summary(report)

        if options["fail_on_regression"] and not report.passed:
            raise CommandError(f"AI Assistant evaluation lab status: {report.status}")

    def _write_summary(self, report):
        self.stdout.write("AI Assistant internal evaluation lab")
        self.stdout.write(f"run_id: {report.run_id}")
        self.stdout.write(f"mode: {report.mode}")
        self.stdout.write(f"status: {report.status}")
        self.stdout.write("")
        libraries = report.ground_truth.get("libraries", {})
        solver = report.ground_truth.get("solver_candidates", {})
        self.stdout.write(f"library ground truth: {json.dumps(libraries, ensure_ascii=False)}")
        self.stdout.write(f"solver readiness: {json.dumps(solver, ensure_ascii=False)}")
        self.stdout.write("")
        for item in report.scenario_preflight:
            marker = "READY" if item["status"] == "ready" else "BLOCKED"
            capabilities = ", ".join(item["capability_ids"]) or "sin mapeo"
            self.stdout.write(f"[{marker}] {item['key']} ({capabilities})")
            for failure in item["failures"]:
                self.stdout.write(
                    f"  - {failure['requirement']}: {failure['reason']}"
                )

        if report.live_validation is not None:
            self.stdout.write("")
            self.stdout.write("live provider results:")
            for result in report.live_validation.scenarios:
                marker = "OK" if result.passed else "FAIL"
                self.stdout.write(f"[{marker}] {result.scenario.key}")
                for check in result.checks:
                    if not check.passed:
                        self.stdout.write(
                            f"  - {check.key} ({check.severity}): {check.detail}"
                        )

        self.stdout.write("")
        self.stdout.write(
            f"diagnostics: {json.dumps(dict(report.diagnostics), ensure_ascii=False)}"
        )
        self.stdout.write(f"cleanup: {json.dumps(dict(report.cleanup), ensure_ascii=False)}")
