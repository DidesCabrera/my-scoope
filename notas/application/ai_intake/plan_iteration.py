from __future__ import annotations

from dataclasses import dataclass

from notas.application.ai_intake.dailyplan_generator import (
    DailyPlanGeneratorError,
    GeneratedDailyPlanProposalResult,
    generate_dailyplan_proposal_from_brief_proposal,
)
from notas.application.ai_intake.iteration_commands import (
    PlanIterationCommandSet,
    parse_dailyplan_iteration_commands,
)
from notas.application.ai_intake.nutrition_brief import NutritionBrief
from notas.application.ai_intake.proposal_from_brief import create_nutrition_brief_proposal
from notas.domain.models import AiNutritionChat, NutritionProposal


@dataclass(frozen=True)
class AiPlanIterationResult:
    source_proposal: NutritionProposal
    proposal: NutritionProposal
    revision_label: str


def should_iterate_generated_plan(*, chat: AiNutritionChat | None, message: str) -> bool:
    if not chat or not chat.proposal_id:
        return False

    proposal = chat.proposal
    payload = proposal.proposed_payload or {}
    if payload.get("intent") != "create_dailyplan":
        return False

    return parse_dailyplan_iteration_commands(message).has_commands


def create_iterated_dailyplan_proposal(
    *,
    user,
    brief: NutritionBrief,
    previous_proposal: NutritionProposal,
    user_message: str,
    source: str = NutritionProposal.SOURCE_AI,
) -> AiPlanIterationResult:
    """Create a new generated DailyPlan proposal revision from chat feedback.

    Patch 13 keeps iteration safe by creating a new reviewable proposal rather
    than mutating an already reviewed/applied proposal. Chat feedback is stored
    as structured commands so each revision is traceable and can be inspected by
    UI, tests or future MCP tools.
    """
    if previous_proposal.created_by_id != user.id:
        raise DailyPlanGeneratorError("dailyplan_iteration_not_allowed")

    command_set = parse_dailyplan_iteration_commands(user_message)
    if not command_set.has_commands:
        raise DailyPlanGeneratorError("dailyplan_iteration_requires_structured_command")

    brief_result = create_nutrition_brief_proposal(
        user=user,
        brief=brief,
        source=source,
    )
    generated_result: GeneratedDailyPlanProposalResult = generate_dailyplan_proposal_from_brief_proposal(
        user=user,
        source_proposal=brief_result.proposal,
        source=source,
    )

    proposal = generated_result.proposal
    current_snapshot = dict(proposal.current_snapshot or {})
    current_snapshot["iteration"] = _build_iteration_metadata(
        previous_proposal=previous_proposal,
        user_message=user_message,
        command_set=command_set,
    )
    proposal.current_snapshot = current_snapshot

    validation_summary = dict(proposal.validation_summary or {})
    validation_summary["chat_iteration"] = _build_iteration_metadata(
        previous_proposal=previous_proposal,
        user_message=user_message,
        command_set=command_set,
    )
    proposal.validation_summary = validation_summary
    proposal.summary = _build_iteration_summary(
        original_summary=proposal.summary,
        user_message=user_message,
    )
    proposal.save(update_fields=["current_snapshot", "validation_summary", "summary"])

    return AiPlanIterationResult(
        source_proposal=brief_result.proposal,
        proposal=proposal,
        revision_label="Propuesta actualizada",
    )


def _build_iteration_metadata(
    *,
    previous_proposal: NutritionProposal,
    user_message: str,
    command_set: PlanIterationCommandSet,
) -> dict:
    return {
        "kind": "chat_feedback_revision",
        "previous_proposal_id": previous_proposal.id,
        "user_message": " ".join((user_message or "").strip().split()),
        "command_set": command_set.as_dict(),
        "command_labels": command_set.labels,
    }


def _build_iteration_summary(*, original_summary: str, user_message: str) -> str:
    feedback = " ".join((user_message or "").strip().split())
    if not feedback:
        return original_summary
    return f"{original_summary} · Ajuste solicitado en chat: {feedback}"
