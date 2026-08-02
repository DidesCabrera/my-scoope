from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from notas.application.ai_intake.model_evaluation import (
    configured_model_evaluation_candidates,
    evaluate_ai_assistant_models,
)
from notas.application.ai_intake.real_provider_validation import (
    built_in_real_provider_scenarios,
    get_validation_user,
)


class Command(BaseCommand):
    help = (
        "Compare AI Assistant quality and cost across configured OpenAI model candidates. "
        "This command consumes real provider usage and, when enabled, AI credits."
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
            "--candidate",
            action="append",
            dest="candidates",
            default=None,
            help="Candidate code to run. Repeat to select several. Defaults to non-benchmark candidates.",
        )
        parser.add_argument(
            "--include-benchmarks",
            action="store_true",
            help="Also run benchmark candidates such as sol_medium.",
        )
        parser.add_argument(
            "--scenario",
            action="append",
            dest="scenarios",
            default=None,
            help="Scenario key to run. Repeat to select several. Defaults to all built-in scenarios.",
        )
        parser.add_argument(
            "--list-candidates",
            action="store_true",
            help="List configured candidates without making provider calls.",
        )
        parser.add_argument(
            "--list-scenarios",
            action="store_true",
            help="List built-in validation scenarios without making provider calls.",
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
            "--fail-on-no-accepted-candidate",
            action="store_true",
            help="Return a non-zero command status when no non-benchmark candidate passes hard checks.",
        )

    def handle(self, *args, **options):
        if options["list_candidates"]:
            self._write_candidates(include_benchmarks=True)
            return
        if options["list_scenarios"]:
            for key, scenario in built_in_real_provider_scenarios().items():
                self.stdout.write(f"{key}: {scenario.description}")
            return

        if not options["live"]:
            raise CommandError(
                "Model evaluation makes real provider calls. "
                "Re-run with --live after reviewing candidates and scenarios."
            )

        try:
            user = get_validation_user(
                user_id=options.get("user_id"),
                email=options.get("user_email") or "",
            )
            report = evaluate_ai_assistant_models(
                user=user,
                candidate_codes=options.get("candidates"),
                include_benchmarks=bool(options.get("include_benchmarks")),
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
            self.stdout.write(self.style.SUCCESS(f"Model evaluation report written: {path}"))

        if options["json"]:
            self.stdout.write(serialized)
        else:
            self._write_summary(payload)

        if options["fail_on_no_accepted_candidate"] and not report.passed:
            raise CommandError("AI Assistant model evaluation found no accepted non-benchmark candidate.")

    def _write_candidates(self, *, include_benchmarks: bool):
        candidates = configured_model_evaluation_candidates(include_benchmarks=include_benchmarks)
        for candidate in candidates:
            marker = " benchmark" if candidate.is_benchmark else ""
            self.stdout.write(
                f"{candidate.code}: {candidate.provider}/{candidate.model} "
                f"reasoning={candidate.reasoning_effort} "
                f"max_output={candidate.max_output_tokens} role={candidate.role}{marker}"
            )

    def _write_summary(self, payload):
        recommendation = dict(payload.get("recommendation") or {})
        self.stdout.write("AI Assistant model quality/cost evaluation")
        self.stdout.write(f"run_id: {payload.get('run_id')}")
        self.stdout.write(f"status: {payload.get('status')}")
        self.stdout.write(
            "accepted: "
            f"{recommendation.get('accepted_candidate') or 'none'} "
            f"{recommendation.get('accepted_model') or ''} "
            f"reasoning={recommendation.get('accepted_reasoning_effort') or ''}"
        )
        self.stdout.write("")
        for result in payload.get("results", []):
            candidate = dict(result.get("candidate") or {})
            quality = dict(result.get("quality_summary") or {})
            cost = dict(result.get("cost_summary") or {})
            self.stdout.write(
                f"[{result.get('status')}] {candidate.get('code')} "
                f"{candidate.get('provider')}/{candidate.get('model')} "
                f"reasoning={candidate.get('reasoning_effort')} "
                f"role={candidate.get('role')}"
            )
            self.stdout.write(
                "  quality: "
                f"scenarios={quality.get('passed_scenarios')}/{quality.get('scenario_count')} "
                f"hard_checks={quality.get('passed_hard_checks')}/{quality.get('hard_check_count')} "
                f"degraded_turns={quality.get('degraded_turns')} "
                f"local_ack_turns={quality.get('local_ack_turns')}"
            )
            self.stdout.write(
                "  cost: "
                f"events={cost.get('event_count')} "
                f"tokens={cost.get('total_tokens')} "
                f"estimated_usd={cost.get('estimated_cost_usd')}"
            )
        self.stdout.write("")
        self.stdout.write("Manual UX review is still required for any accepted model.")
