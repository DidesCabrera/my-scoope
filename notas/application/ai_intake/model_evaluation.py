from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Mapping, Sequence

from django.conf import settings

from ai_assistant.application.chat_engines import ChatEngine
from notas.application.ai_intake.real_provider_validation import (
    OUTCOME_FIRST_ACTION_TYPE,
    RealProviderValidationReport,
    run_real_provider_validation,
)

MODEL_EVALUATION_VERSION = "ai_assistant.model_quality_cost.v1"
DEFAULT_BENCHMARK_ROLE = "benchmark"


@dataclass(frozen=True)
class AIModelEvaluationCandidate:
    code: str
    provider: str
    model: str
    reasoning_effort: str
    max_output_tokens: int
    role: str = "candidate"

    @property
    def is_benchmark(self) -> bool:
        return self.role == DEFAULT_BENCHMARK_ROLE

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "provider": self.provider,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "max_output_tokens": self.max_output_tokens,
            "role": self.role,
            "benchmark": self.is_benchmark,
        }


@dataclass(frozen=True)
class AIModelEvaluationCandidateResult:
    candidate: AIModelEvaluationCandidate
    report: RealProviderValidationReport
    quality_summary: Mapping[str, Any]
    cost_summary: Mapping[str, Any]

    @property
    def passed(self) -> bool:
        return bool(self.report.passed)

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.as_dict(),
            "status": "passed" if self.passed else "hard_regression",
            "quality_summary": dict(self.quality_summary),
            "cost_summary": dict(self.cost_summary),
            "validation_report": self.report.as_dict(),
        }


@dataclass(frozen=True)
class AIModelEvaluationReport:
    version: str
    run_id: str
    user_id: int
    scenario_keys: Sequence[str]
    results: Sequence[AIModelEvaluationCandidateResult]
    recommendation: Mapping[str, Any]

    @property
    def passed(self) -> bool:
        return any(result.passed and not result.candidate.is_benchmark for result in self.results)

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "run_id": self.run_id,
            "status": "candidate_accepted" if self.passed else "no_candidate_passed",
            "user_id": self.user_id,
            "scenario_keys": list(self.scenario_keys),
            "recommendation": dict(self.recommendation),
            "results": [result.as_dict() for result in self.results],
        }


EngineFactory = Callable[[AIModelEvaluationCandidate], ChatEngine | None]


def configured_model_evaluation_candidates(
    *,
    candidate_codes: Sequence[str] | None = None,
    include_benchmarks: bool = False,
) -> tuple[AIModelEvaluationCandidate, ...]:
    raw = getattr(settings, "AI_ASSISTANT_MODEL_EVALUATION_CANDIDATES", {}) or {}
    if not isinstance(raw, Mapping):
        raw = {}

    selected_codes = {str(code or "").strip() for code in tuple(candidate_codes or ())}
    candidates: list[AIModelEvaluationCandidate] = []
    for code, payload in raw.items():
        candidate = _candidate_from_payload(str(code or ""), payload)
        if candidate is None:
            continue
        if selected_codes and candidate.code not in selected_codes:
            continue
        if candidate.is_benchmark and not include_benchmarks and not selected_codes:
            continue
        candidates.append(candidate)

    if selected_codes:
        found = {candidate.code for candidate in candidates}
        missing = sorted(selected_codes - found)
        if missing:
            raise ValueError(f"Unknown AI model evaluation candidate(s): {', '.join(missing)}.")
    return tuple(candidates)


def evaluate_ai_assistant_models(
    *,
    user: Any,
    candidates: Sequence[AIModelEvaluationCandidate] | None = None,
    candidate_codes: Sequence[str] | None = None,
    include_benchmarks: bool = False,
    scenario_keys: Sequence[str] | None = None,
    run_id: str | None = None,
    engine_factory: EngineFactory | None = None,
) -> AIModelEvaluationReport:
    selected_candidates = tuple(
        candidates
        or configured_model_evaluation_candidates(
            candidate_codes=candidate_codes,
            include_benchmarks=include_benchmarks,
        )
    )
    if not selected_candidates:
        raise ValueError("No AI model evaluation candidates are configured.")
    if not getattr(user, "pk", None):
        raise ValueError("AI model evaluation requires one persisted authenticated user.")

    root_run_id = run_id or uuid.uuid4().hex
    results: list[AIModelEvaluationCandidateResult] = []
    for candidate in selected_candidates:
        with _candidate_settings(candidate):
            candidate_report = run_real_provider_validation(
                user=user,
                scenario_keys=scenario_keys,
                engine=engine_factory(candidate) if engine_factory else None,
                run_id=_candidate_run_id(root_run_id, candidate.code),
            )
        results.append(
            AIModelEvaluationCandidateResult(
                candidate=candidate,
                report=candidate_report,
                quality_summary=_quality_summary(candidate_report),
                cost_summary=_cost_summary(candidate_report),
            )
        )

    recommendation = _recommendation(results)
    return AIModelEvaluationReport(
        version=MODEL_EVALUATION_VERSION,
        run_id=root_run_id,
        user_id=int(user.pk),
        scenario_keys=tuple(scenario_keys or ()),
        results=tuple(results),
        recommendation=recommendation,
    )


@contextmanager
def _candidate_settings(candidate: AIModelEvaluationCandidate):
    route = {
        "provider": candidate.provider,
        "model": candidate.model,
        "max_output_tokens": candidate.max_output_tokens,
        "reason": f"model_quality_cost_eval:{candidate.code}",
    }
    assignments = {
        "AI_ASSISTANT_LLM_PROVIDER": candidate.provider,
        "AI_ASSISTANT_OPENAI_MODEL": candidate.model,
        "AI_ASSISTANT_OPENAI_REASONING_EFFORT": candidate.reasoning_effort,
        "AI_ASSISTANT_MAX_OUTPUT_TOKENS": candidate.max_output_tokens,
        "AI_ASSISTANT_LLM_MODEL_ROUTES": {
            "default": route,
            OUTCOME_FIRST_ACTION_TYPE: route,
        },
    }
    originals = {name: getattr(settings, name, None) for name in assignments}
    try:
        for name, value in assignments.items():
            setattr(settings, name, value)
        yield
    finally:
        for name, value in originals.items():
            setattr(settings, name, value)


def _candidate_from_payload(code: str, payload: Any) -> AIModelEvaluationCandidate | None:
    if not code or not isinstance(payload, Mapping):
        return None
    provider = str(payload.get("provider") or "openai").strip().lower()
    model = str(payload.get("model") or "").strip()
    reasoning_effort = str(payload.get("reasoning_effort") or "low").strip().lower()
    role = str(payload.get("role") or "candidate").strip().lower()
    try:
        max_output_tokens = int(payload.get("max_output_tokens") or 0)
    except (TypeError, ValueError):
        max_output_tokens = 0
    if not provider or not model or max_output_tokens <= 0:
        return None
    return AIModelEvaluationCandidate(
        code=code,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        max_output_tokens=max_output_tokens,
        role=role,
    )


def _candidate_run_id(root_run_id: str, code: str) -> str:
    return f"{root_run_id[:14]}-{code.replace('_', '-')}"[:28]


def _quality_summary(report: RealProviderValidationReport) -> dict[str, Any]:
    checks = [check for scenario in report.scenarios for check in scenario.checks]
    hard_checks = [check for check in checks if check.severity == "hard"]
    passed_hard = [check for check in hard_checks if check.passed]
    turns = [turn for scenario in report.scenarios for turn in scenario.turns]
    scenario_count = len(tuple(report.scenarios))
    passed_scenarios = sum(1 for scenario in report.scenarios if scenario.passed)
    return {
        "passed": report.passed,
        "scenario_count": scenario_count,
        "passed_scenarios": passed_scenarios,
        "scenario_pass_rate": _ratio(passed_scenarios, scenario_count),
        "hard_check_count": len(hard_checks),
        "passed_hard_checks": len(passed_hard),
        "hard_check_pass_rate": _ratio(len(passed_hard), len(hard_checks)),
        "hard_failure_count": len(report.hard_failures),
        "turn_count": len(turns),
        "degraded_turns": sum(1 for turn in turns if turn.fallback),
        "provider_followup_failed_turns": sum(1 for turn in turns if turn.provider_tool_followup_failed),
        "local_ack_turns": sum(1 for turn in turns if turn.tool_followup_local_ack),
        "native_tool_calls": sum(int(turn.provider_native_tool_calls or 0) for turn in turns),
        "manual_review_required": True,
    }


def _cost_summary(report: RealProviderValidationReport) -> dict[str, Any]:
    usage = dict(report.usage_summary or {})
    return {
        "event_count": int(usage.get("event_count") or 0),
        "input_tokens": int(usage.get("input_tokens") or 0),
        "cached_input_tokens": int(usage.get("cached_input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
        "estimated_cost_usd": str(usage.get("estimated_cost_usd") or "0"),
    }


def _recommendation(results: Sequence[AIModelEvaluationCandidateResult]) -> dict[str, Any]:
    non_benchmarks = [result for result in results if not result.candidate.is_benchmark]
    baseline = next((result for result in non_benchmarks if result.candidate.role == "baseline"), None)
    passing = [result for result in non_benchmarks if result.passed]
    accepted = baseline if baseline is not None and baseline.passed else (passing[0] if passing else None)
    baseline_cost = _decimal_cost(baseline) if baseline is not None else None

    payload: dict[str, Any] = {
        "accepted_candidate": accepted.candidate.code if accepted is not None else "",
        "accepted_model": accepted.candidate.model if accepted is not None else "",
        "accepted_reasoning_effort": accepted.candidate.reasoning_effort if accepted is not None else "",
        "decision": "accept_baseline" if accepted is baseline and accepted is not None else "",
        "needs_manual_ux_review": accepted is not None,
        "notes": [],
    }
    if accepted is not None and accepted is not baseline:
        payload["decision"] = "escalate_to_first_passing_candidate"
    if accepted is None:
        payload["decision"] = "no_candidate_passed"
        payload["notes"].append("No non-benchmark candidate passed the hard automated checks.")
    elif baseline is not None and not baseline.passed:
        payload["notes"].append("Baseline failed hard checks; use the accepted escalation candidate while fixing gaps.")
    else:
        payload["notes"].append("Baseline passed automated checks; keep manual UX review before release.")

    comparisons = []
    for result in results:
        item: dict[str, Any] = {
            "candidate": result.candidate.code,
            "model": result.candidate.model,
            "passed": result.passed,
            "estimated_cost_usd": result.cost_summary.get("estimated_cost_usd"),
        }
        if baseline_cost is not None:
            item["cost_delta_vs_baseline_usd"] = str(_decimal_cost(result) - baseline_cost)
        comparisons.append(item)
    payload["cost_comparison"] = comparisons
    return payload


def _decimal_cost(result: AIModelEvaluationCandidateResult | None) -> Decimal:
    if result is None:
        return Decimal("0")
    try:
        return Decimal(str(result.cost_summary.get("estimated_cost_usd") or "0"))
    except Exception:
        return Decimal("0")


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)
