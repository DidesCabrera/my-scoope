from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    build_required_follow_up_questions,
    build_summary_items,
    serialize_brief,
)
from notas.domain.models import (
    NutritionProposal,
    NutritionProposalAuditEvent,
)

AI_NUTRITION_BRIEF_INTENT = "ai_nutrition_brief"
AI_INTAKE_SOURCE = "home_ai_intake"


@dataclass(frozen=True)
class AiNutritionBriefProposalResult:
    proposal: NutritionProposal


def create_nutrition_brief_proposal(
    *,
    user,
    brief: NutritionBrief,
) -> AiNutritionBriefProposalResult:
    """Create a reviewable NutritionProposal from the editable intake brief.

    This command intentionally does not create DailyPlans, Meals, Programs, or
    proposal payloads that can be applied automatically. Patch 3 only preserves
    the user's validated brief as a reviewable proposal artifact. The future
    generator can consume this proposal/brief and replace it with a concrete
    create_dailyplan proposal later.
    """
    follow_up_questions = build_required_follow_up_questions(brief)

    if follow_up_questions:
        raise ValueError("nutrition_brief_has_pending_questions")

    title = _build_proposal_title(brief)
    summary = _build_proposal_summary(brief)
    targets = _build_targets(brief)
    proposed_payload = _build_proposed_payload(brief)
    validation_summary = _build_validation_summary(brief)

    with transaction.atomic():
        proposal = NutritionProposal.objects.create(
            dailyplan=None,
            created_by=user,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            source=NutritionProposal.SOURCE_AI,
            title=title,
            summary=summary,
            targets=targets,
            current_snapshot={
                "source": AI_INTAKE_SOURCE,
                "kind": "nutrition_brief",
                "message": "No hay DailyPlan base asociado; esta propuesta nace desde Home AI Intake.",
            },
            proposed_payload=proposed_payload,
            validation_summary=validation_summary,
        )

        NutritionProposalAuditEvent.objects.create(
            proposal=proposal,
            actor=user,
            action=NutritionProposalAuditEvent.ACTION_CREATED,
            status_before="",
            status_after=proposal.status,
            message="Nutrition brief proposal created from Home AI Intake.",
            metadata={
                "source": AI_INTAKE_SOURCE,
                "intent": AI_NUTRITION_BRIEF_INTENT,
                "requested_entity": brief.requested_entity,
            },
        )

    return AiNutritionBriefProposalResult(
        proposal=proposal,
    )


def _build_proposal_title(brief: NutritionBrief) -> str:
    entity_label = brief.requested_entity_label
    goal_label = brief.goal_label

    if brief.goal:
        return f"Brief IA - {entity_label} para {goal_label.lower()}"

    return f"Brief IA - {entity_label}"


def _build_proposal_summary(brief: NutritionBrief) -> str:
    pieces = [
        f"Solicitud original: {brief.raw_prompt or 'Sin prompt original'}",
        f"Objetivo: {brief.goal_label}",
        f"Tipo de solución: {brief.requested_entity_label}",
    ]

    if brief.meals_per_day:
        pieces.append(f"Comidas por día: {brief.meals_per_day}")

    if brief.training_frequency is not None:
        pieces.append(f"Entrenamiento: {brief.training_frequency} veces/semana")

    if brief.style_preferences:
        pieces.append(f"Estilo: {', '.join(brief.style_preferences)}")

    if brief.excluded_foods:
        pieces.append(f"Exclusiones: {', '.join(brief.excluded_foods)}")

    return " · ".join(pieces)


def _build_targets(brief: NutritionBrief) -> dict:
    targets = {}

    if brief.calorie_target is not None:
        targets["total_kcal"] = brief.calorie_target

    if brief.protein_target is not None:
        targets["protein"] = brief.protein_target

    if brief.carb_target is not None:
        targets["carbs"] = brief.carb_target

    if brief.fat_target is not None:
        targets["fat"] = brief.fat_target

    return targets


def _build_proposed_payload(brief: NutritionBrief) -> dict:
    return {
        "intent": AI_NUTRITION_BRIEF_INTENT,
        "source": AI_INTAKE_SOURCE,
        "requested_entity": brief.requested_entity,
        "nutrition_brief": serialize_brief(brief),
        "generator_status": {
            "state": "ready_for_future_generator",
            "message": "Brief listo para el futuro generador de DailyPlans/Programs; no contiene entidades aplicables todavía.",
        },
        "safety_boundary": "La IA conversa y estructura; MyScoope deberá calcular, validar y optimizar; el usuario revisa y aprueba.",
    }


def _build_validation_summary(brief: NutritionBrief) -> dict:
    return {
        "kind": "nutrition_brief_review",
        "status": "ready_for_generator",
        "summary_items": [
            {
                "label": item.label,
                "value": item.value,
                "is_pending": item.is_pending,
            }
            for item in build_summary_items(brief)
        ],
        "next_step": "dailyplan_proposal_generator",
    }
