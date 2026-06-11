from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.urls import reverse

from notas.application.dto.proposal_dto import (
    NutritionProposalDTO,
    NutritionProposalListItemDTO,
)
from notas.domain.models import NutritionProposal


def _serialize_datetime(value):
    if value is None:
        return None

    return value.isoformat()


def _format_received_at(value) -> str:
    if value is None:
        return "Sin fecha de recepción"

    if timezone.is_naive(value):
        received_at = value
    else:
        received_at = timezone.localtime(value)

    return received_at.strftime("%d-%m-%Y")


def get_available_proposal_queryset(user):
    """
    Propuestas visibles para el usuario.

    Regla inicial conservadora:
    - propuestas creadas por el usuario;
    - propuestas asociadas a DailyPlans propios del usuario.

    No se incluyen todavía propuestas de DailyPlans compartidos, porque eso
    requiere una decisión de producto más fina sobre permisos de revisión.
    """
    return (
        NutritionProposal.objects
        .select_related(
            "dailyplan",
            "created_by",
            "reviewed_by",
            "applied_by",
        )
        .prefetch_related(
            "audit_events",
            "audit_events__actor",
        )
        .filter(
            Q(created_by=user)
            | Q(dailyplan__created_by=user)
        )
        .distinct()
        .order_by("list_order", "-created_at", "-id")
    )


def _get_proposal_intent(proposal: NutritionProposal) -> str:
    payload = proposal.proposed_payload or {}

    if not isinstance(payload, dict):
        return ""

    return str(payload.get("intent") or "")


def _get_proposal_attachment(proposal: NutritionProposal) -> dict[str, str]:
    """
    Adjuntos visibles en la lista de propuestas.

    La propuesta todavía no necesariamente creó una entidad real, por eso
    preferimos describir el entregable propuesto antes que enlazarlo.
    """
    payload = proposal.proposed_payload or {}

    if not isinstance(payload, dict):
        payload = {}

    intent = _get_proposal_intent(proposal)

    if intent == "create_meal":
        meal = payload.get("meal") or {}
        return {
            "kind": "meal",
            "label": "Comida propuesta",
            "name": meal.get("name") or proposal.title,
            "icon": "utensils",
        }

    if intent == "create_dailyplan":
        dailyplan = payload.get("dailyplan") or {}
        return {
            "kind": "dailyplan",
            "label": "DailyPlan propuesto",
            "name": dailyplan.get("name") or proposal.dailyplan.name,
            "icon": "clipboard-list",
        }

    return {
        "kind": "dailyplan",
        "label": "DailyPlan asociado",
        "name": proposal.dailyplan.name,
        "icon": "clipboard-list",
    }


def _build_proposal_list_actions(proposal: NutritionProposal) -> list[dict]:
    detail_url = reverse("proposal_detail", args=[proposal.id])
    delete_url = reverse("proposal_delete", args=[proposal.id])

    return [
        {
            "key": "detail",
            "label": "Ver propuesta",
            "icon": "arrow-right",
            "url": detail_url,
            "method": "get",
            "desktop_position": "inline",
            "mobile_position": "inline",
        },
        {
            "key": "delete",
            "label": "Eliminar propuesta",
            "icon": "trash-2",
            "url": delete_url,
            "method": "post",
            "desktop_position": "menu",
            "mobile_position": "menu",
        },
    ]


def build_proposal_list_item_dto(
    proposal: NutritionProposal,
) -> NutritionProposalListItemDTO:
    attachment = _get_proposal_attachment(proposal)

    return NutritionProposalListItemDTO(
        id=proposal.id,
        dailyplan_id=proposal.dailyplan_id,
        dailyplan_name=proposal.dailyplan.name,
        created_by_id=proposal.created_by_id,
        created_by_username=proposal.created_by.username,
        reviewed_by_id=proposal.reviewed_by_id,
        reviewed_by_username=(
            proposal.reviewed_by.username
            if proposal.reviewed_by
            else None
        ),
        status=proposal.status,
        source=proposal.source,
        title=proposal.title,
        summary=proposal.summary,
        attachment_kind=attachment["kind"],
        attachment_label=attachment["label"],
        attachment_name=attachment["name"],
        attachment_icon=attachment["icon"],
        actions=_build_proposal_list_actions(proposal),
        is_reviewable=proposal.is_reviewable,
        is_final=proposal.is_final,
        created_at=_serialize_datetime(proposal.created_at),
        received_at_label=_format_received_at(proposal.created_at),
        reviewed_at=_serialize_datetime(proposal.reviewed_at),
    )


def build_proposal_audit_event_dto(
    event,
) -> dict:
    return {
        "id": event.id,
        "action": event.action,
        "actor_id": event.actor_id,
        "actor_username": (
            event.actor.username
            if event.actor
            else None
        ),
        "status_before": event.status_before,
        "status_after": event.status_after,
        "message": event.message,
        "metadata": event.metadata or {},
        "created_at": _serialize_datetime(event.created_at),
    }


def build_proposal_audit_events_dto(
    proposal: NutritionProposal,
) -> list[dict]:
    return [
        build_proposal_audit_event_dto(event)
        for event in proposal.audit_events.all().order_by(
            "created_at",
            "id",
        )
    ]


def build_proposal_dto(
    proposal: NutritionProposal,
) -> NutritionProposalDTO:
    return NutritionProposalDTO(
        id=proposal.id,
        dailyplan_id=proposal.dailyplan_id,
        dailyplan_name=proposal.dailyplan.name,
        created_by_id=proposal.created_by_id,
        created_by_username=proposal.created_by.username,
        reviewed_by_id=proposal.reviewed_by_id,
        reviewed_by_username=(
            proposal.reviewed_by.username
            if proposal.reviewed_by
            else None
        ),
        status=proposal.status,
        source=proposal.source,
        title=proposal.title,
        summary=proposal.summary,
        targets=proposal.targets or {},
        current_snapshot=proposal.current_snapshot or {},
        proposed_payload=proposal.proposed_payload or {},
        validation_summary=proposal.validation_summary or {},
        audit_events=build_proposal_audit_events_dto(proposal),
        is_reviewable=proposal.is_reviewable,
        is_final=proposal.is_final,
        created_at=_serialize_datetime(proposal.created_at),
        received_at_label=_format_received_at(proposal.created_at),
        reviewed_at=_serialize_datetime(proposal.reviewed_at),
        applied_at=_serialize_datetime(proposal.applied_at),
    )


def list_user_proposals(
    user,
    *,
    status_filter: str | None = None,
) -> list[NutritionProposalListItemDTO]:
    proposals = get_available_proposal_queryset(user)

    if status_filter == NutritionProposal.STATUS_PENDING_REVIEW:
        proposals = proposals.filter(
            status=NutritionProposal.STATUS_PENDING_REVIEW,
        )
    elif status_filter == NutritionProposal.STATUS_APPROVED:
        proposals = proposals.filter(
            status=NutritionProposal.STATUS_APPROVED,
        )

    return [
        build_proposal_list_item_dto(proposal)
        for proposal in proposals
    ]


def list_dailyplan_proposals(
    user,
    dailyplan_id: int,
) -> list[NutritionProposalListItemDTO]:
    proposals = (
        get_available_proposal_queryset(user)
        .filter(dailyplan_id=dailyplan_id)
    )

    return [
        build_proposal_list_item_dto(proposal)
        for proposal in proposals
    ]


def search_proposals(
    user,
    query: str,
) -> list[NutritionProposalListItemDTO]:
    query = (query or "").strip()

    proposals = get_available_proposal_queryset(user)

    if query:
        proposals = proposals.filter(
            Q(title__icontains=query)
            | Q(summary__icontains=query)
            | Q(dailyplan__name__icontains=query)
        )

    return [
        build_proposal_list_item_dto(proposal)
        for proposal in proposals
    ]


def get_proposal_detail(
    user,
    proposal_id: int,
) -> NutritionProposalDTO:
    proposal = get_object_or_404(
        get_available_proposal_queryset(user),
        pk=proposal_id,
    )

    return build_proposal_dto(proposal)