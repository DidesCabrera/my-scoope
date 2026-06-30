"""Contratos de negocio para NutritionProposal.

Este módulo concentra reglas semánticas compartidas por interface,
presentation y application para evitar que cada borde vuelva a inferir
intents, estados aplicables o labels de propuesta por su cuenta.
"""

from dataclasses import asdict, dataclass
from typing import Any

from notas.application.dto.proposal_payloads import (
    CREATE_DAILYPLAN_INTENT,
    CREATE_MEAL_INTENT,
)

AI_NUTRITION_BRIEF_INTENT = "ai_nutrition_brief"

PROPOSAL_STATUS_DRAFT = "draft"
PROPOSAL_STATUS_PENDING_REVIEW = "pending_review"
PROPOSAL_STATUS_APPROVED = "approved"
PROPOSAL_STATUS_REJECTED = "rejected"
PROPOSAL_STATUS_CANCELLED = "cancelled"
PROPOSAL_STATUS_APPLIED = "applied"


@dataclass(frozen=True)
class ProposalIntentContract:
    intent: str
    entity_title: str
    attachment_kind: str
    attachment_label: str
    attachment_icon: str
    is_create_meal: bool = False
    is_create_dailyplan: bool = False
    is_apply_supported: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


_UNKNOWN_CONTRACT = ProposalIntentContract(
    intent="",
    entity_title="Entidad en la propuesta",
    attachment_kind="dailyplan",
    attachment_label="DailyPlan asociado",
    attachment_icon="clipboard-list",
)

_INTENT_CONTRACTS = {
    CREATE_MEAL_INTENT: ProposalIntentContract(
        intent=CREATE_MEAL_INTENT,
        entity_title="Comida en la propuesta",
        attachment_kind="meal",
        attachment_label="Comida propuesta",
        attachment_icon="utensils",
        is_create_meal=True,
        is_apply_supported=True,
    ),
    CREATE_DAILYPLAN_INTENT: ProposalIntentContract(
        intent=CREATE_DAILYPLAN_INTENT,
        entity_title="DailyPlan en la propuesta",
        attachment_kind="dailyplan",
        attachment_label="DailyPlan propuesto",
        attachment_icon="clipboard-list",
        is_create_dailyplan=True,
        is_apply_supported=True,
    ),
    AI_NUTRITION_BRIEF_INTENT: ProposalIntentContract(
        intent=AI_NUTRITION_BRIEF_INTENT,
        entity_title="Brief nutricional en la propuesta",
        attachment_kind="brief",
        attachment_label="Brief nutricional",
        attachment_icon="clipboard-list",
    ),
}

_STATUS_LABELS = {
    PROPOSAL_STATUS_DRAFT: "Borrador",
    PROPOSAL_STATUS_PENDING_REVIEW: "Pendiente",
    PROPOSAL_STATUS_APPROVED: "Aprobada",
    PROPOSAL_STATUS_REJECTED: "Rechazada",
    PROPOSAL_STATUS_CANCELLED: "Cancelada",
    PROPOSAL_STATUS_APPLIED: "Aplicada",
}

FINAL_STATUSES = frozenset({
    PROPOSAL_STATUS_REJECTED,
    PROPOSAL_STATUS_CANCELLED,
    PROPOSAL_STATUS_APPLIED,
})


def normalize_proposal_intent(intent: Any) -> str | None:
    if not isinstance(intent, str):
        return None

    clean_intent = intent.strip()

    if not clean_intent:
        return None

    return clean_intent


def resolve_proposal_intent(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None

    return normalize_proposal_intent(payload.get("intent"))


def get_proposal_intent_contract(intent: Any) -> ProposalIntentContract:
    clean_intent = normalize_proposal_intent(intent)

    if not clean_intent:
        return _UNKNOWN_CONTRACT

    return _INTENT_CONTRACTS.get(clean_intent, _UNKNOWN_CONTRACT)


def is_apply_supported_intent(intent: Any) -> bool:
    return get_proposal_intent_contract(intent).is_apply_supported


def can_apply_proposal(
    *,
    status: Any,
    intent: Any,
    applied_at: Any = None,
) -> bool:
    return (
        status == PROPOSAL_STATUS_APPROVED
        and is_apply_supported_intent(intent)
        and not applied_at
    )


def proposal_status_label(status: Any) -> str:
    if not isinstance(status, str):
        return ""

    clean_status = status.strip()

    if not clean_status:
        return ""

    return _STATUS_LABELS.get(clean_status, clean_status)
