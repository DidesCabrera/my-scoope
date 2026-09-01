from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ninja import Router

from mobile_api.api_support import proposal_error, require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.schema_domains.proposals import ProposalApplyInput, ProposalDetailEnvelope, ProposalListEnvelope
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors import proposal_detail_payload, proposal_list_payload
from notas.application.proposals.contracts import (
    CREATE_DAILYPLAN_INTENT,
    CREATE_MEAL_INTENT,
    resolve_proposal_intent,
)
from notas.application.proposals.subject_context_warnings import proposal_requires_external_subject_ack
from notas.application.queries.proposal_queries import get_available_proposal_queryset
from notas.application.services.commands.proposal_commands import (
    apply_approved_create_dailyplan_proposal,
    apply_approved_create_meal_proposal,
    approve_proposal,
    cancel_proposal,
    reject_proposal,
)
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router(auth=mobile_bearer)


def _owned_proposal(user: Any, proposal_id: int) -> Any:
    proposal = get_available_proposal_queryset(user).filter(pk=proposal_id).first()
    if proposal is None:
        raise proposal_error(ValueError("proposal_not_found"))
    return proposal


def _proposal_state_action(
    request: Any,
    proposal_id: int,
    command: Callable[..., Any],
) -> dict[str, Any]:
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    proposal = _owned_proposal(request.auth.user, proposal_id)
    try:
        command(user=request.auth.user, proposal=proposal)
    except ValueError as exc:
        raise proposal_error(exc) from exc
    return success(proposal_detail_payload(request.auth.user, proposal_id))


@router.get(
    "/proposals",
    response={200: ProposalListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
    operation_id="mobile_api_api_proposals",
)
def proposals(request: Any, status: str | None = None, offset: int = 0, limit: int = 30) -> dict[str, Any]:
    return success(proposal_list_payload(request.auth.user, status_filter=status, offset=offset, limit=limit))


@router.get(
    "/proposals/{proposal_id}",
    response={200: ProposalDetailEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
    operation_id="mobile_api_api_proposal_detail",
)
def proposal_detail(request: Any, proposal_id: int) -> dict[str, Any]:
    payload = proposal_detail_payload(request.auth.user, proposal_id)
    if payload is None:
        raise proposal_error(ValueError("proposal_not_found"))
    return success(payload)


@router.post(
    "/proposals/{proposal_id}/approve",
    response={200: ProposalDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
    operation_id="mobile_api_api_approve_mobile_proposal",
)
def approve_mobile_proposal(request: Any, proposal_id: int) -> dict[str, Any]:
    return _proposal_state_action(request, proposal_id, approve_proposal)


@router.post(
    "/proposals/{proposal_id}/reject",
    response={200: ProposalDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
    operation_id="mobile_api_api_reject_mobile_proposal",
)
def reject_mobile_proposal(request: Any, proposal_id: int) -> dict[str, Any]:
    return _proposal_state_action(request, proposal_id, reject_proposal)


@router.post(
    "/proposals/{proposal_id}/cancel",
    response={200: ProposalDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
    operation_id="mobile_api_api_cancel_mobile_proposal",
)
def cancel_mobile_proposal(request: Any, proposal_id: int) -> dict[str, Any]:
    return _proposal_state_action(request, proposal_id, cancel_proposal)


@router.post(
    "/proposals/{proposal_id}/apply",
    response={200: ProposalDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
    operation_id="mobile_api_api_apply_mobile_proposal",
)
def apply_mobile_proposal(request: Any, proposal_id: int, payload: ProposalApplyInput) -> dict[str, Any]:
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    proposal = _owned_proposal(request.auth.user, proposal_id)
    if proposal_requires_external_subject_ack(proposal) and not payload.acknowledge_external_subject:
        raise proposal_error(ValueError("proposal_external_subject_ack_required"))
    intent = resolve_proposal_intent(proposal.proposed_payload)
    try:
        if intent == CREATE_MEAL_INTENT:
            apply_approved_create_meal_proposal(user=request.auth.user, proposal=proposal)
        elif intent == CREATE_DAILYPLAN_INTENT:
            apply_approved_create_dailyplan_proposal(user=request.auth.user, proposal=proposal)
        else:
            raise ValueError("proposal_apply_not_supported")
    except ValueError as exc:
        raise proposal_error(exc) from exc
    return success(proposal_detail_payload(request.auth.user, proposal_id))
