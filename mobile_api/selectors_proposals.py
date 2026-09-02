from __future__ import annotations

from notas.application.proposals.contracts import (
    can_apply_proposal,
    proposal_status_label,
    resolve_proposal_intent,
)
from notas.application.queries.proposal_queries import (
    build_proposal_dto,
    build_proposal_list_item_dto,
    get_available_proposal_queryset,
)
from notas.presentation.proposals.proposal_review_viewmodels import build_proposal_review_vm


def _proposal_actions(*, status: str, intent: str | None, applied_at=None) -> list[dict]:
    if status == "pending_review":
        return [
            {"key": "approve", "label": "Aprobar", "tone": "default", "requires_confirmation": True},
            {"key": "reject", "label": "Rechazar", "tone": "danger", "requires_confirmation": True},
            {"key": "cancel", "label": "Cancelar", "tone": "danger", "requires_confirmation": True},
        ]
    if can_apply_proposal(status=status, intent=intent, applied_at=applied_at):
        return [
            {"key": "apply", "label": "Aplicar", "tone": "default", "requires_confirmation": True},
            {"key": "cancel", "label": "Cancelar", "tone": "danger", "requires_confirmation": True},
        ]
    if status in {"draft", "approved"}:
        return [{"key": "cancel", "label": "Cancelar", "tone": "danger", "requires_confirmation": True}]
    return []


def _proposal_summary_payload(dto: dict) -> dict:
    intent = resolve_proposal_intent(dto.get("proposed_payload"))
    return {
        "id": dto["id"],
        "title": dto.get("title", ""),
        "summary": dto.get("summary", ""),
        "status": dto.get("status", "draft"),
        "status_label": proposal_status_label(dto.get("status", "")),
        "source": dto.get("source", ""),
        "attachment_kind": dto.get("attachment_kind", "dailyplan"),
        "attachment_label": dto.get("attachment_label", ""),
        "attachment_name": dto.get("attachment_name", ""),
        "is_reviewable": bool(dto.get("is_reviewable")),
        "created_at": dto.get("created_at"),
        "actions": _proposal_actions(
            status=dto.get("status", ""),
            intent=intent,
            applied_at=dto.get("applied_at"),
        ),
    }


def proposal_list_payload(user, *, status_filter=None, offset=0, limit=30) -> dict:
    queryset = get_available_proposal_queryset(user)
    pending_count = queryset.filter(status="pending_review").count()
    allowed_filters = {"pending_review", "approved", "applied", "rejected", "cancelled"}
    if status_filter in allowed_filters:
        queryset = queryset.filter(status=status_filter)
    safe_offset = max(int(offset or 0), 0)
    safe_limit = min(max(int(limit or 30), 1), 50)
    total = queryset.count()
    items = [
        _proposal_summary_payload(
            {
                **build_proposal_list_item_dto(proposal).as_dict(),
                "proposed_payload": proposal.proposed_payload,
                "applied_at": proposal.applied_at,
            }
        )
        for proposal in queryset[safe_offset : safe_offset + safe_limit]
    ]
    return {
        "items": items,
        "total": total,
        "offset": safe_offset,
        "limit": safe_limit,
        "pending_count": pending_count,
    }


def _fact_label(value: str) -> str:
    labels = {
        "total_kcal": "Calorías",
        "protein": "Proteína",
        "protein_g": "Proteína",
        "carbs": "Carbohidratos",
        "carbs_g": "Carbohidratos",
        "fat": "Grasas",
        "fat_g": "Grasas",
        "is_valid": "Validación",
        "intent": "Tipo",
    }
    return labels.get(value, value.replace("_", " ").strip().capitalize())


def _bounded_facts(value, *, prefix="", limit=20) -> list[dict]:
    facts: list[dict] = []

    def visit(candidate, path: str) -> None:
        if len(facts) >= limit:
            return
        if isinstance(candidate, dict):
            for key, child in candidate.items():
                if key in {"subject_context", "suggested_changes", "foods", "meals"}:
                    continue
                visit(child, f"{path}.{key}" if path else str(key))
            return
        if isinstance(candidate, (str, int, float, bool)) and path:
            key = path.split(".")[-1]
            display = "Sí" if candidate is True else "No" if candidate is False else str(candidate)
            facts.append({"label": _fact_label(key), "value": display})

    visit(value, prefix)
    return facts


def _proposal_kpis_payload(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    return {key: value.get(key) for key in ("total_kcal", "protein", "carbs", "fat", "ppk")}


def _proposal_meal_payload(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    return {
        "name": value.get("name", ""),
        "foods": [
            {
                "food_id": food.get("food_id"),
                "food_name": food.get("food_name", ""),
                "quantity": food.get("quantity"),
                "unit": food.get("unit", "g"),
            }
            for food in value.get("foods", [])
            if isinstance(food, dict)
        ],
        "kpis": _proposal_kpis_payload(value.get("kpis")),
    }


def _proposal_dailyplan_payload(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    return {
        "name": value.get("name", ""),
        "meals": [
            {
                "hour": item.get("hour"),
                "note": item.get("note", ""),
                "meal": _proposal_meal_payload(item.get("meal")),
            }
            for item in value.get("meals", [])
            if isinstance(item, dict) and isinstance(item.get("meal"), dict)
        ],
        "kpis": _proposal_kpis_payload(value.get("kpis")),
    }


def proposal_detail_payload(user, proposal_id: int) -> dict | None:
    proposal = get_available_proposal_queryset(user).filter(pk=proposal_id).first()
    if proposal is None:
        return None
    dto = build_proposal_dto(proposal).as_dict()
    review = build_proposal_review_vm(dto).as_dict()
    summary = _proposal_summary_payload({**dto, **build_proposal_list_item_dto(proposal).as_dict()})
    warning = review["subject_context_warning"]
    applied = review.get("applied_result")
    return {
        **summary,
        "dailyplan_id": dto.get("dailyplan_id"),
        "dailyplan_name": dto.get("dailyplan_name", ""),
        "created_by_username": dto.get("created_by_username", ""),
        "reviewed_by_username": dto.get("reviewed_by_username"),
        "intent": review["payload"].get("intent"),
        "entity_title": review["payload"].get("entity_title", ""),
        "target_facts": _bounded_facts(dto.get("targets", {})),
        "current_facts": _bounded_facts(
            dto.get("current_snapshot", {}).get("actual", dto.get("current_snapshot", {}))
        ),
        "validation_facts": _bounded_facts(dto.get("validation_summary", {}).get("payload_validation", {})),
        "meal": _proposal_meal_payload(review["payload"].get("meal")),
        "dailyplan": _proposal_dailyplan_payload(review["payload"].get("dailyplan")),
        "subject_context_warning": {
            "requires_warning": warning.get("requires_warning", False),
            "source_label": warning.get("source_label", ""),
            "calculation_weight_label": warning.get("calculation_weight_label", ""),
            "title": warning.get("title", ""),
            "message": warning.get("message", ""),
        },
        "applied_result": (
            {
                "kind": applied.get("kind"),
                "object_id": applied.get("object_id"),
                "object_name": applied.get("object_name", ""),
            }
            if applied
            else None
        ),
        "applied_at": dto.get("applied_at"),
    }
