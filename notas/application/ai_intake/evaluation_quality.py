"""Quality gates for AI Assistant evaluation trajectories.

The deterministic validation harness already proves transport, tool and mutation
invariants.  This module adds the missing product-quality layer without reducing
the result to one score that can hide a serious failure.

Human judgements are explicit inputs.  An absent review is pending, never a pass.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

QUALITY_EVALUATION_VERSION = "ai_assistant.quality_evaluation.v1"
QUALITY_ANNOTATIONS_VERSION = "ai_assistant.quality_annotations.v1"

HUMAN_QUALITY_CRITERIA = (
    "helpfulness",
    "naturalness",
    "clarity",
    "appropriate_next_step",
)

AUTOMATED_QUALITY_CHECKS = {
    "prepared_patch_exact": "operation_correctness",
    "program_proposal_complete": "operation_correctness",
    "expected_outcome": "outcome_completion",
    "tool_contract": "tool_selection_and_arguments",
    "state_mutation_boundary": "state_and_approval_boundary",
    "visible_facts": "grounding",
    "tool_result_grounding": "grounding",
    "stable_captured_facts": "context_continuity",
    "known_facts_not_reasked": "context_continuity",
    "brief_transitions": "context_continuity",
    "response_repetition": "interaction_efficiency",
    "response_semantic_repetition": "interaction_efficiency",
    "card_pacing": "interaction_efficiency",
}


def evaluate_semantic_repetition(turns: Sequence[Any], *, maximum: int = 1) -> tuple[bool, str]:
    """Detect repeated substantive clauses, not only identical openings."""

    clauses: list[str] = []
    locations: dict[str, list[int]] = defaultdict(list)
    for turn in turns:
        for clause in _substantive_clauses(getattr(turn, "assistant_message", "")):
            clauses.append(clause)
            locations[clause].append(int(getattr(turn, "index", 0) or 0))

    repeated = {
        clause: indexes
        for clause, indexes in locations.items()
        if len(indexes) > maximum and len(set(indexes)) > 1
    }
    if not repeated:
        return True, f"{len(clauses)} substantive response clause(s) were not repeated across turns"

    detail = "; ".join(
        f"{clause!r} on turns {indexes}"
        for clause, indexes in sorted(repeated.items())
    )
    return False, f"repeated substantive response clauses: {detail}"


def grade_validation_reports(
    reports: Sequence[Any],
    *,
    annotations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Grade all scenario trajectories and expose reliability across repetitions."""

    normalized_annotations = _normalize_annotations(annotations)
    runs: list[dict[str, Any]] = []
    scenario_statuses: dict[str, list[str]] = defaultdict(list)

    for report in reports:
        run_id = str(getattr(report, "run_id", "") or "")
        for result in tuple(getattr(report, "scenarios", ()) or ()):
            scenario_key = str(getattr(result.scenario, "key", "") or "")
            instance_key = f"{run_id}/{scenario_key}"
            annotation = normalized_annotations.get(instance_key)
            graded = grade_scenario_result(
                result,
                run_id=run_id,
                annotation=annotation,
            )
            runs.append(graded)
            scenario_statuses[scenario_key].append(str(graded["status"]))

    reliability = {}
    for scenario_key, statuses in sorted(scenario_statuses.items()):
        passed_runs = sum(1 for status in statuses if status == "passed")
        automated_runs = sum(
            1 for status in statuses if status not in {"hard_regression", "quality_regression"}
        )
        reliability[scenario_key] = {
            "run_count": len(statuses),
            "passed_runs": passed_runs,
            "automated_successful_runs": automated_runs,
            "pass_rate": _ratio(passed_runs, len(statuses)),
            "pass_all": bool(statuses) and passed_runs == len(statuses),
            "statuses": statuses,
        }

    counts = Counter(str(item["status"]) for item in runs)
    if counts["hard_regression"]:
        status = "hard_regression"
    elif counts["quality_regression"]:
        status = "quality_regression"
    elif counts["awaiting_human_review"]:
        status = "awaiting_human_review"
    elif runs:
        status = "passed"
    else:
        status = "not_run"

    return {
        "version": QUALITY_EVALUATION_VERSION,
        "status": status,
        "passed": status == "passed",
        "scenario_run_count": len(runs),
        "status_counts": dict(sorted(counts.items())),
        "human_review": {
            "required_criteria": list(HUMAN_QUALITY_CRITERIA),
            "reviewed_runs": sum(
                1 for item in runs if item["human_review"]["status"] in {"passed", "failed"}
            ),
            "pending_runs": sum(
                1 for item in runs if item["human_review"]["status"] == "pending"
            ),
        },
        "reliability": reliability,
        "runs": runs,
    }


def build_quality_annotation_template(reports: Sequence[Any]) -> dict[str, Any]:
    """Build one explicit review slot per scenario run, including repetitions."""

    reviews: dict[str, Any] = {}
    for report in reports:
        run_id = str(getattr(report, "run_id", "") or "")
        for result in tuple(getattr(report, "scenarios", ()) or ()):
            scenario = getattr(result, "scenario", None)
            scenario_key = str(getattr(scenario, "key", "") or "")
            key = f"{run_id}/{scenario_key}"
            reviews[key] = {
                "scenario": scenario_key,
                "expected_outcome": str(
                    getattr(scenario, "expected_outcome", "response_only")
                    or "response_only"
                ),
                "criteria": dict.fromkeys(HUMAN_QUALITY_CRITERIA, "pending"),
                "reviewer": "",
                "reviewer_kind": "human",
                "notes": "",
            }
    return {
        "version": QUALITY_ANNOTATIONS_VERSION,
        "instructions": "Replace every pending value with pass or fail after reviewing the complete trajectory.",
        "reviews": reviews,
    }


def grade_scenario_result(
    result: Any,
    *,
    run_id: str,
    annotation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    checks = tuple(getattr(result, "checks", ()) or ())
    automated: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for check in checks:
        dimension = AUTOMATED_QUALITY_CHECKS.get(str(getattr(check, "key", "") or ""))
        if not dimension:
            continue
        automated[dimension].append(
            {
                "check": str(getattr(check, "key", "") or ""),
                "passed": bool(getattr(check, "passed", False)),
                "detail": str(getattr(check, "detail", "") or ""),
            }
        )

    automated_dimensions = {
        dimension: {
            "passed": bool(items) and all(item["passed"] for item in items),
            "checks": items,
        }
        for dimension, items in sorted(automated.items())
    }
    hard_failures = [
        {
            "check": str(getattr(check, "key", "") or ""),
            "detail": str(getattr(check, "detail", "") or ""),
        }
        for check in checks
        if str(getattr(check, "severity", "") or "") == "hard"
        and not bool(getattr(check, "passed", False))
    ]
    automated_quality_failures = [
        dimension
        for dimension, payload in automated_dimensions.items()
        if not payload["passed"]
    ]
    human_review = _grade_human_annotation(annotation)

    if hard_failures:
        status = "hard_regression"
    elif automated_quality_failures:
        status = "quality_regression"
    elif human_review["status"] == "failed":
        status = "quality_regression"
    elif human_review["status"] == "pending":
        status = "awaiting_human_review"
    else:
        status = "passed"

    scenario = result.scenario
    return {
        "run_id": run_id,
        "scenario": str(getattr(scenario, "key", "") or ""),
        "expected_outcome": str(getattr(scenario, "expected_outcome", "response_only") or "response_only"),
        "status": status,
        "passed": status == "passed",
        "hard_failures": hard_failures,
        "automated_quality_failures": automated_quality_failures,
        "automated_dimensions": automated_dimensions,
        "human_review": human_review,
    }


def _grade_human_annotation(annotation: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(annotation, Mapping):
        return {
            "status": "pending",
            "criteria": {},
            "notes": "",
        }

    if annotation.get("reviewer_kind") != "human" or not str(annotation.get("reviewer") or "").strip():
        return {
            "status": "pending",
            "criteria": {},
            "notes": str(annotation.get("notes") or ""),
            "reason": "named_human_reviewer_required",
        }
    raw_criteria = annotation.get("criteria")
    criteria = dict(raw_criteria) if isinstance(raw_criteria, Mapping) else {}
    normalized = {
        key: str(criteria.get(key) or "").strip().lower()
        for key in HUMAN_QUALITY_CRITERIA
    }
    invalid = {
        key: value
        for key, value in normalized.items()
        if value not in {"pass", "fail"}
    }
    if invalid:
        return {
            "status": "pending",
            "criteria": normalized,
            "notes": str(annotation.get("notes") or ""),
            "invalid_or_missing_criteria": sorted(invalid),
        }
    return {
        "status": "failed" if "fail" in normalized.values() else "passed",
        "criteria": normalized,
        "notes": str(annotation.get("notes") or ""),
        "reviewer": str(annotation.get("reviewer") or ""),
    }


def _normalize_annotations(value: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return {}
    if value.get("version") not in {None, "", QUALITY_ANNOTATIONS_VERSION}:
        raise ValueError(
            f"Unsupported quality annotations version: {value.get('version')}"
        )
    reviews = value.get("reviews", value)
    if not isinstance(reviews, Mapping):
        raise ValueError("Quality annotations reviews must be an object.")
    return {
        str(key): dict(item)
        for key, item in reviews.items()
        if isinstance(item, Mapping)
    }


def _substantive_clauses(value: Any) -> list[str]:
    text = str(value or "")
    raw_clauses = re.split(r"[.!?\n]+", text)
    clauses = []
    for raw in raw_clauses:
        normalized = _normalize_text(raw)
        if len(normalized.split()) >= 6:
            clauses.append(normalized)
    return clauses


def _normalize_text(value: Any) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", without_marks))


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


__all__ = [
    "HUMAN_QUALITY_CRITERIA",
    "QUALITY_ANNOTATIONS_VERSION",
    "QUALITY_EVALUATION_VERSION",
    "evaluate_semantic_repetition",
    "build_quality_annotation_template",
    "grade_scenario_result",
    "grade_validation_reports",
]
