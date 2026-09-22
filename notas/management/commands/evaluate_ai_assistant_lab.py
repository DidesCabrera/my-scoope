from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from notas.application.ai_intake.evaluation_lab import (
    DEFAULT_LAB_SCENARIOS,
    run_evaluation_lab,
)
from notas.application.ai_intake.evaluation_quality import (
    build_quality_annotation_template,
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
        parser.add_argument(
            "--charge-user-credits",
            action="store_true",
            help=(
                "Charge the selected user's AI quota during --live. By default the internal "
                "lab records provider usage without consuming that user's credits."
            ),
        )
        parser.add_argument(
            "--repetitions",
            type=int,
            default=1,
            help="Repeat every ready live scenario 1-10 times to measure reliability.",
        )
        parser.add_argument(
            "--quality-annotations",
            default="",
            help=(
                "Optional JSON file with explicit human quality reviews. "
                "Without it, a healthy live run remains awaiting_quality_review."
            ),
        )
        parser.add_argument("--output", default="", help="Optional JSON report path.")
        parser.add_argument(
            "--annotation-template-output",
            default="",
            help="Optional JSON path for the explicit human-review worksheet.",
        )
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
                self.stdout.write(
                    f"{key} [{capabilities}] outcome={scenario.expected_outcome}: "
                    f"{scenario.description}"
                )
            return

        try:
            user = get_validation_user(
                user_id=options.get("user_id"),
                email=options.get("user_email") or "",
            )
            quality_annotations = self._read_quality_annotations(
                options.get("quality_annotations") or ""
            )
            report = run_evaluation_lab(
                user=user,
                scenario_keys=options.get("scenarios"),
                live=bool(options.get("live")),
                cleanup_review_artifacts=not bool(options.get("keep_artifacts")),
                charge_user_credits=bool(options.get("charge_user_credits")),
                repetitions=int(options.get("repetitions") or 1),
                quality_annotations=quality_annotations,
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

        annotation_path_text = str(
            options.get("annotation_template_output") or ""
        ).strip()
        if annotation_path_text:
            annotation_path = Path(annotation_path_text)
            annotation_path.parent.mkdir(parents=True, exist_ok=True)
            annotation_path.write_text(
                json.dumps(
                    build_quality_annotation_template(report.live_validations),
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Quality annotation template written: {annotation_path}"
                )
            )

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
        self.stdout.write(f"billing: {json.dumps(dict(report.billing), ensure_ascii=False)}")
        self.stdout.write(
            f"quality: {json.dumps(dict(report.quality_evaluation), ensure_ascii=False)}"
        )
        self.stdout.write(
            f"task dataset: {json.dumps(dict(report.task_dataset), ensure_ascii=False)}"
        )
        self.stdout.write(
            f"product feedback: {json.dumps(dict(report.product_feedback), ensure_ascii=False)}"
        )
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

    @staticmethod
    def _read_quality_annotations(path_value):
        path_text = str(path_value or "").strip()
        if not path_text:
            return None
        path = Path(path_text)
        if not path.exists():
            raise ValueError(f"Quality annotations file does not exist: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Quality annotations file must contain a JSON object.")
        return payload
