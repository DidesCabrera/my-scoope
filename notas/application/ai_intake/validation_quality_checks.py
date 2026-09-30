from __future__ import annotations

from typing import Any, Mapping, Sequence

from notas.application.ai_intake.evaluation_quality import evaluate_semantic_repetition
from notas.application.ai_intake.real_provider_behavior_checks import (
    evaluate_expected_outcome,
)


def build_validation_quality_check_specs(
    scenario: Any,
    turns: Sequence[Any],
    *,
    state_before: Mapping[str, Any],
    state_after: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    outcome_passed, outcome_detail = evaluate_expected_outcome(
        scenario,
        turns,
        state_before=state_before,
        state_after=state_after,
    )
    repetition_passed, repetition_detail = evaluate_semantic_repetition(turns)
    return {
        "expected_outcome": {
            "key": "expected_outcome",
            "passed": outcome_passed,
            "detail": outcome_detail,
            "severity": "hard",
        },
        "semantic_repetition": {
            "key": "response_semantic_repetition",
            "passed": repetition_passed,
            "detail": repetition_detail,
            "severity": "quality",
        },
        "manual_review": {
            "key": "manual_ux_review",
            "passed": False,
            "detail": f"{len(scenario.manual_review_prompts)} qualitative prompt(s) require human review",
            "severity": "manual",
        },
    }
