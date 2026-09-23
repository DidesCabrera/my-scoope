"""Internal, UI-independent evaluation lab for the AI nutrition assistant.

The lab deliberately separates four questions that were previously mixed in a
single chat transcript:

1. Is the selected user's persisted fixture suitable for the request?
2. Can the deterministic data/solver layer produce the expected ground truth?
3. Does the real model select and execute the correct product capability?
4. Did the run respect the review boundary and leave final entities untouched?

It reuses the real-provider validation engine instead of inventing a second
assistant runtime. Provider execution is always opt-in at the command boundary.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections import Counter, defaultdict
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from django.conf import settings
from django.test.utils import override_settings

from ai_assistant.models import AIPreparedAction
from notas.application.ai_intake.capability_scenarios import PATCH_CASES
from notas.application.ai_intake.evaluation_artifacts import capture_review_artifacts
from notas.application.ai_intake.evaluation_dataset import evaluate_assistant_task_dataset
from notas.application.ai_intake.evaluation_quality import grade_validation_reports
from notas.application.ai_intake.message_feedback import summarize_message_feedback
from notas.application.ai_intake.program_scenarios import PROGRAM_SCENARIOS
from notas.application.ai_intake.real_provider_validation import (
    RealProviderValidationReport,
    _specialize_scenario_for_user,
    built_in_real_provider_scenarios,
    run_real_provider_validation,
)
from notas.application.queries.library_queries import (
    dailyplan_library_queryset,
    food_library_queryset,
    meal_library_queryset,
    program_library_queryset,
)
from notas.application.queries.solver_food_candidates import list_solver_food_candidates
from notas.domain.models import NutritionProposal
from nutrition_solver.application.contracts import (
    OptimizationInput,
    OptimizationStatus,
    optimize_meal_portions,
)
from nutrition_solver.domain.models import MacroTarget

EVALUATION_LAB_VERSION = "ai_assistant.evaluation_lab.v2"
DEFAULT_LAB_SCENARIOS = (
    "saludo_y_descubrimiento",
    "tema_externo_breve",
    "capacidades_en_lenguaje_de_producto",
    "referencia_ambigua_sin_tools",
    "ficha_conocida_sin_repreguntas",
    "datos_agrupados_y_cards",
    "cambio_de_direccion",
    "error_de_tool_y_recuperacion",
    "bibliotecas_coherentes",
    "comida_450_kcal",
    "reemplazo_alimento_200g",
    "plan_2400_distribucion_30_50_20",
) + tuple(case[0] for case in PATCH_CASES) + PROGRAM_SCENARIOS

_CATALOG_ROW_PATTERN = re.compile(
    r"^\| (?P<id>(?:PR|F|M|DP|PG|C|X|A)-\d{2}) "
    r"\| (?P<request>.+?) \| (?P<resolution>.+?) "
    r"\| (?P<coverage>.+?) \| (?P<observation>.+?) \|$"
)

_CHECK_DIAGNOSTIC_DOMAIN = {
    "visible_boundary": "guardrail_policy",
    "llm_only_runtime": "runtime_configuration",
    "provider_health": "provider_transport",
    "natural_provider_contract": "provider_transport",
    "expected_brief": "language_understanding",
    "profile_fixture": "catalog_data",
    "stable_captured_facts": "conversation_state",
    "known_facts_not_reasked": "conversation_state",
    "brief_transitions": "language_understanding",
    "tool_contract": "tool_routing",
    "visible_facts": "grounding",
    "behavioral_surface": "guardrail_policy",
    "expected_outcome": "outcome_completion",
    "response_repetition": "response_quality",
    "tool_result_grounding": "grounding",
    "provider_followup_health": "provider_transport",
    "post_tool_fallback_pacing": "guardrail_policy",
    "card_pacing": "guardrail_policy",
    "usage_observability": "observability",
    "state_mutation_boundary": "state_mutation",
    "prepared_patch_exact": "operation_correctness",
    "program_proposal_complete": "operation_correctness",
}

_CREDIT_BLOCK_REASONS = {
    "account_credit_wallet_limit_exceeded",
    "credit_quota_hard_blocked",
    "daily_credit_limit_exceeded",
    "monthly_credit_limit_exceeded",
}


@dataclass(frozen=True)
class EvaluationLabReport:
    run_id: str
    user_id: int
    mode: str
    status: str
    catalog: Mapping[str, Any]
    ground_truth: Mapping[str, Any]
    scenario_preflight: Sequence[Mapping[str, Any]]
    live_validation: RealProviderValidationReport | None
    live_validations: Sequence[RealProviderValidationReport]
    quality_evaluation: Mapping[str, Any]
    task_dataset: Mapping[str, Any]
    product_feedback: Mapping[str, Any]
    diagnostics: Mapping[str, Any]
    cleanup: Mapping[str, Any]
    billing: Mapping[str, Any]

    @property
    def passed(self) -> bool:
        return self.status in {"preflight_ready", "passed"}

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": EVALUATION_LAB_VERSION,
            "run_id": self.run_id,
            "user_id": self.user_id,
            "mode": self.mode,
            "status": self.status,
            "passed": self.passed,
            "catalog": dict(self.catalog),
            "ground_truth": dict(self.ground_truth),
            "scenario_preflight": [dict(item) for item in self.scenario_preflight],
            "quality_evaluation": dict(self.quality_evaluation),
            "task_dataset": dict(self.task_dataset),
            "product_feedback": dict(self.product_feedback),
            "diagnostics": dict(self.diagnostics),
            "cleanup": dict(self.cleanup),
            "billing": dict(self.billing),
            "live_validation": (
                self.live_validation.as_dict() if self.live_validation is not None else None
            ),
            "live_validations": [report.as_dict() for report in self.live_validations],
        }


def run_evaluation_lab(
    *,
    user: Any,
    scenario_keys: Sequence[str] | None = None,
    live: bool = False,
    engine: Any | None = None,
    run_id: str | None = None,
    cleanup_review_artifacts: bool = True,
    charge_user_credits: bool = False,
    repetitions: int = 1,
    quality_annotations: Mapping[str, Any] | None = None,
) -> EvaluationLabReport:
    if not getattr(user, "pk", None):
        raise ValueError("AI Assistant evaluation lab requires a persisted authenticated user.")
    if not 1 <= int(repetitions) <= 10:
        raise ValueError("AI Assistant evaluation repetitions must be between 1 and 10.")

    selected_keys = tuple(scenario_keys or DEFAULT_LAB_SCENARIOS)
    catalog = built_in_real_provider_scenarios()
    unknown = [key for key in selected_keys if key not in catalog]
    if unknown:
        raise ValueError(f"Unknown evaluation lab scenario(s): {', '.join(unknown)}")

    validation_run_id = run_id or uuid.uuid4().hex
    task_dataset = evaluate_assistant_task_dataset()
    specialized = {
        key: _specialize_scenario_for_user(catalog[key], user=user)
        for key in selected_keys
    }
    logger = logging.getLogger("myscoope.assistant.runtime")
    logger.info("lab_preflight_start run_id=%s", validation_run_id)
    ground_truth = _build_ground_truth(user=user, scenarios=specialized)
    logger.info("lab_preflight_done run_id=%s", validation_run_id)
    preflight = tuple(
        _scenario_preflight(scenario, ground_truth=ground_truth)
        for scenario in specialized.values()
    )
    ready_keys = tuple(
        item["key"] for item in preflight if item["status"] == "ready"
    )
    blocked = tuple(item for item in preflight if item["status"] != "ready")

    live_reports: list[RealProviderValidationReport] = []
    cleanup = {
        "enabled": bool(cleanup_review_artifacts),
        "nutrition_proposals_deleted": 0,
        "prepared_actions_deleted": 0,
        "retained_artifact_ids": [],
    }
    created_artifacts = {"nutrition_proposals": set(), "prepared_actions": set()}
    if live and ready_keys:
        try:
            credit_context = (
                nullcontext()
                if charge_user_credits
                else override_settings(AI_ASSISTANT_CREDITS_ENABLED=False)
            )
            with credit_context, capture_review_artifacts(user) as created_artifacts:
                for repetition in range(1, int(repetitions) + 1):
                    logger.info("lab_provider_start repetition=%s", repetition)
                    repetition_run_id = (
                        validation_run_id
                        if int(repetitions) == 1
                        else f"{validation_run_id[:24]}-r{repetition}"
                    )
                    live_reports.append(
                        run_real_provider_validation(
                            user=user,
                            scenario_keys=ready_keys,
                            engine=engine,
                            run_id=repetition_run_id,
                        )
                    )
                    logger.info("lab_provider_done repetition=%s passed=%s", repetition, live_reports[-1].passed)
        finally:
            if cleanup_review_artifacts:
                cleanup = _cleanup_new_review_artifacts(user=user, created=created_artifacts)

    diagnostics = _build_diagnostics(
        preflight=preflight,
        live_reports=live_reports,
    )
    quality_evaluation = grade_validation_reports(
        live_reports,
        annotations=quality_annotations,
    )
    credit_blocks = sorted(
        {
            reason
            for live_report in live_reports
            for reason in _credit_block_reasons(live_report)
        }
    )
    if not task_dataset["passed"]:
        status = "dataset_regression"
    elif not live:
        status = "preflight_ready" if not blocked else "blocked_by_fixture"
    elif credit_blocks:
        status = "blocked_by_credit_quota"
    elif any(not live_report.passed for live_report in live_reports):
        status = "hard_regression"
    elif quality_evaluation["status"] == "quality_regression":
        status = "quality_regression"
    elif blocked or not live_reports:
        status = "blocked_by_fixture"
    elif quality_evaluation["status"] in {"awaiting_human_review", "not_run"}:
        status = "awaiting_quality_review"
    else:
        status = "passed"

    return EvaluationLabReport(
        run_id=validation_run_id,
        user_id=int(user.pk),
        mode="live_provider" if live else "deterministic_preflight",
        status=status,
        catalog=_catalog_summary(specialized),
        ground_truth=ground_truth,
        scenario_preflight=preflight,
        live_validation=live_reports[0] if live_reports else None,
        live_validations=tuple(live_reports),
        quality_evaluation=quality_evaluation,
        task_dataset=task_dataset,
        product_feedback=summarize_message_feedback(days=30, user=user),
        diagnostics=diagnostics,
        cleanup=cleanup,
        billing={
            "policy": "charge_selected_user" if charge_user_credits else "internal_unmetered",
            "user_credits_charged": bool(charge_user_credits),
            "provider_usage_recorded": bool(live),
            "credit_block_reasons": credit_blocks,
        },
    )


def _build_ground_truth(*, user: Any, scenarios: Mapping[str, Any]) -> dict[str, Any]:
    from notas.application.culinary_library import load_culinary_candidates
    culinary, _ = load_culinary_candidates(user=user)
    candidates = list_solver_food_candidates(user, limit=250)
    role_counts = Counter(candidate.role for candidate in candidates.candidates)
    solver_450 = _solver_450_probe(candidates.candidates)
    specialized_truth = {
        key: dict(scenario.ground_truth)
        for key, scenario in scenarios.items()
    }
    return {
        "culinary_library": {"variants": len(culinary), "families": len({c.family for c in culinary})},
        "libraries": {
            "foods": food_library_queryset(user).count(),
            "meals": meal_library_queryset(user).count(),
            "dailyplans": dailyplan_library_queryset(user).count(),
            "programs": program_library_queryset(user).count(),
            "source": "canonical_web_library_projections",
        },
        "solver_candidates": {
            "returned_count": candidates.count,
            "total_eligible_count": candidates.total_eligible_count,
            "active_visible_count": candidates.active_visible_count,
            "excluded_solver_disabled_count": candidates.excluded_solver_disabled_count,
            "role_counts": dict(sorted(role_counts.items())),
            "readiness": candidates.as_dict()["readiness"],
        },
        "solver_450_probe": solver_450,
        "scenarios": specialized_truth,
    }


def _solver_450_probe(candidates: Sequence[Any]) -> dict[str, Any]:
    if not candidates:
        return {
            "status": "blocked",
            "reason_code": "no_solver_enabled_foods",
            "target": {"kcal": 450, "protein": 33.75, "carbs": 56.25, "fat": 10},
        }
    result = optimize_meal_portions(
        OptimizationInput(
            target=MacroTarget(kcal=450, protein=33.75, carbs=56.25, fat=10),
            candidate_foods=tuple(candidates),
            meal_slots=("evaluation_lab_meal",),
            context={"source": EVALUATION_LAB_VERSION},
        )
    )
    payload = result.as_dict()
    return {
        "status": str(getattr(result.status, "value", result.status)),
        "feasible": result.status != OptimizationStatus.IMPOSSIBLE and bool(result.portions),
        "target": {"kcal": 450, "protein": 33.75, "carbs": 56.25, "fat": 10},
        "result": payload,
    }


def _scenario_preflight(scenario: Any, *, ground_truth: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    solver_candidates = ground_truth["solver_candidates"]
    scenario_truth = ground_truth["scenarios"].get(scenario.key, {})
    for requirement in scenario.fixture_requirements:
        if requirement == "capability_fixture" and scenario_truth.get("missing_fixture_fields"):
            failures.append({"requirement": requirement, "reason": "missing:" + ",".join(scenario_truth["missing_fixture_fields"])})
        if requirement == "owned_dailyplan" and not scenario_truth.get("context_dailyplan_id"):
            failures.append({"requirement": requirement, "reason": "no_owned_dailyplan"})
        elif requirement == "solver_candidates" and not solver_candidates["total_eligible_count"]:
            failures.append({"requirement": requirement, "reason": "no_solver_enabled_foods"})
        elif requirement == "culinary_library" and not ground_truth.get("culinary_library", {}).get("variants"):
            failures.append({"requirement": requirement, "reason": "no_validated_culinary_variants"})
        elif requirement == "solver_450_feasible":
            probe = ground_truth["solver_450_probe"]
            if not probe.get("feasible"):
                failures.append(
                    {
                        "requirement": requirement,
                        "reason": str(probe.get("reason_code") or probe.get("status") or "solver_impossible"),
                    }
                )
        elif requirement == "meal_replacement_fixture":
            required = ("meal_id", "source_food_id", "replacement_food_id")
            missing = [key for key in required if not scenario_truth.get(key)]
            if missing:
                failures.append(
                    {
                        "requirement": requirement,
                        "reason": f"missing:{','.join(missing)}",
                    }
                )

    return {
        "key": scenario.key,
        "description": scenario.description,
        "capability_ids": list(scenario.capability_ids),
        "diagnostic_domains": list(scenario.diagnostic_domains),
        "mutation_policy": scenario.mutation_policy,
        "expected_outcome": scenario.expected_outcome,
        "status": "ready" if not failures else "blocked_by_fixture",
        "failures": failures,
        "ground_truth": dict(scenario_truth),
    }


def _catalog_summary(scenarios: Mapping[str, Any]) -> dict[str, Any]:
    path = (
        Path(settings.BASE_DIR)
        / "docs"
        / "00_current"
        / "features"
        / "ai_assistant"
        / "user_request_capability_catalog.md"
    )
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            match = _CATALOG_ROW_PATTERN.match(line)
            if match:
                rows.append(match.groupdict())
    mapped = {
        capability_id
        for scenario in scenarios.values()
        for capability_id in scenario.capability_ids
    }
    identifiers = {row["id"] for row in rows}
    return {
        "total_capabilities": len(rows),
        "coverage_states": dict(sorted(Counter(row["coverage"] for row in rows).items())),
        "selected_live_scenarios": len(scenarios),
        "expected_outcomes": dict(
            sorted(Counter(scenario.expected_outcome for scenario in scenarios.values()).items())
        ),
        "mapped_capability_ids": sorted(mapped),
        "mapped_capability_count": len(mapped),
        "unknown_mapped_capability_ids": sorted(mapped.difference(identifiers)),
        "catalog_path": str(path),
    }


def _build_diagnostics(
    *,
    preflight: Sequence[Mapping[str, Any]],
    live_report: RealProviderValidationReport | None = None,
    live_reports: Sequence[RealProviderValidationReport] = (),
) -> dict[str, Any]:
    failures_by_domain: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in preflight:
        for failure in item.get("failures", []):
            domain = (
                "solver_feasibility"
                if failure.get("requirement") == "solver_450_feasible"
                else "catalog_data"
            )
            failures_by_domain[domain].append(
                {
                    "scenario": str(item["key"]),
                    "check": str(failure.get("requirement") or "fixture"),
                    "detail": str(failure.get("reason") or "fixture_not_ready"),
                }
            )

    reports = tuple(live_reports or ()) or ((live_report,) if live_report is not None else ())
    for current_live_report in reports:
        for result in current_live_report.scenarios:
            blocked_reasons = _scenario_credit_block_reasons(result)
            if blocked_reasons:
                failures_by_domain["credit_quota"].append(
                    {
                        "scenario": result.scenario.key,
                        "check": "credit_preflight",
                        "detail": ",".join(blocked_reasons),
                    }
                )
                # Missing tools, proposals and captured facts are consequences of
                # the provider turn never starting, not assistant regressions.
                continue
            for check in result.checks:
                if check.passed or check.severity not in {"hard", "diagnostic"}:
                    continue
                domain = _CHECK_DIAGNOSTIC_DOMAIN.get(check.key, "unknown")
                failures_by_domain[domain].append(
                    {
                        "scenario": result.scenario.key,
                        "check": check.key,
                        "detail": check.detail,
                    }
                )
            for turn in result.turns:
                for tool_result in turn.tool_results:
                    status = str(tool_result.get("status") or "")
                    if status in {"", "ok"}:
                        continue
                    if result.scenario.expected_tool_errors.get(str(tool_result.get("tool_name") or "")) == status:
                        continue
                    code = " ".join(
                        str(tool_result.get(key) or "")
                        for key in ("error_code", "code", "error_message", "message")
                    ).lower()
                    if "no_eligible" in code or "candidate" in code:
                        domain = "catalog_data"
                    elif "impossible" in code or "feasible" in code or "solver" in code:
                        domain = "solver_feasibility"
                    elif "safety" in code or "allerg" in code:
                        domain = "guardrail_policy"
                    else:
                        domain = "tool_execution"
                    failures_by_domain[domain].append(
                        {
                            "scenario": result.scenario.key,
                            "check": str(tool_result.get("tool_name") or "tool_result"),
                            "detail": code.strip() or status,
                        }
                    )

    return {
        "failure_count": sum(len(items) for items in failures_by_domain.values()),
        "failed_domains": sorted(failures_by_domain),
        "by_domain": dict(sorted(failures_by_domain.items())),
        "interpretation": (
            "No automated failure was detected. Manual UX review still applies to live runs."
            if not failures_by_domain
            else "Failures are grouped by the layer most likely responsible; inspect the transcript and ground truth before changing prompts or tools."
        ),
    }


def _scenario_credit_block_reasons(result: Any) -> list[str]:
    return sorted(
        {
            str(turn.usage_observability.get("error_type") or "")
            for turn in result.turns
            if str(turn.usage_observability.get("error_type") or "")
            in _CREDIT_BLOCK_REASONS
        }
    )


def _credit_block_reasons(
    live_report: RealProviderValidationReport | None,
) -> list[str]:
    if live_report is None:
        return []
    return sorted(
        {
            reason
            for result in live_report.scenarios
            for reason in _scenario_credit_block_reasons(result)
        }
    )


def _review_artifact_ids(user: Any) -> dict[str, set[int]]:
    return {
        "nutrition_proposals": set(
            NutritionProposal.objects.filter(created_by=user).values_list("id", flat=True)
        ),
        "prepared_actions": set(
            AIPreparedAction.objects.filter(user=user).values_list("id", flat=True)
        ),
    }


def _cleanup_new_review_artifacts(*, user: Any, created: Mapping[str, set[int]]) -> dict[str, Any]:
    proposal_ids = created.get("nutrition_proposals", set())
    action_ids = created.get("prepared_actions", set())

    deletable_proposals = NutritionProposal.objects.filter(
        created_by=user,
        id__in=proposal_ids,
        status__in=(
            NutritionProposal.STATUS_DRAFT,
            NutritionProposal.STATUS_PENDING_REVIEW,
        ),
    )
    deleted_proposal_ids = set(deletable_proposals.values_list("id", flat=True))
    deletable_actions = AIPreparedAction.objects.filter(
        user=user,
        id__in=action_ids,
        status=AIPreparedAction.Status.PREPARED,
    )
    deleted_action_ids = set(deletable_actions.values_list("id", flat=True))
    deletable_proposals.delete()
    deletable_actions.delete()
    retained = sorted(
        [f"nutrition_proposal:{value}" for value in proposal_ids - deleted_proposal_ids]
        + [f"prepared_action:{value}" for value in action_ids - deleted_action_ids]
    )
    return {
        "enabled": True,
        "nutrition_proposals_deleted": len(deleted_proposal_ids),
        "prepared_actions_deleted": len(deleted_action_ids),
        "retained_artifact_ids": retained,
    }


__all__ = [
    "DEFAULT_LAB_SCENARIOS",
    "EVALUATION_LAB_VERSION",
    "EvaluationLabReport",
    "run_evaluation_lab",
]
