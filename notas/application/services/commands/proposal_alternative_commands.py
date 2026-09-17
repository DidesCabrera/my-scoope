from __future__ import annotations

from django.db import transaction
from django.db.models import Q, Subquery

from notas.application.queries.proposal_simulation_queries import simulate_proposal_payload
from notas.application.validation.proposal_payload_validators import validate_proposal_payload_or_raise
from notas.domain.models import NutritionProposal, NutritionProposalAuditEvent


@transaction.atomic
def select_proposal_alternative(*, user, proposal: NutritionProposal, alternative_id: str) -> NutritionProposal:
    """Select a server-stored solver alternative while a proposal is reviewable."""

    owned_proposal_ids = NutritionProposal.objects.filter(
        Q(created_by=user) | Q(dailyplan__created_by=user)
    ).values("pk")
    locked = (
        NutritionProposal.objects.select_for_update()
        .filter(pk=proposal.pk, pk__in=Subquery(owned_proposal_ids))
        .first()
    )
    if locked is None:
        raise ValueError("proposal_not_available")
    if locked.status != NutritionProposal.STATUS_PENDING_REVIEW:
        raise ValueError("proposal_alternative_not_reviewable")

    snapshot = dict(locked.current_snapshot or {})
    solver = dict(snapshot.get("nutrition_solver") or {})
    alternatives = tuple(solver.get("alternatives") or ())
    selected = next(
        (
            item
            for item in alternatives
            if str(item.get("alternative_id") or "") == str(alternative_id or "")
        ),
        None,
    )
    if selected is None:
        raise ValueError("proposal_alternative_not_found")

    payload = dict(selected.get("payload") or {})
    validate_proposal_payload_or_raise(payload)
    simulation = simulate_proposal_payload(user=user, payload=payload).as_dict()

    solver["selected_alternative_id"] = selected["alternative_id"]
    snapshot["nutrition_solver"] = solver
    validation_summary = dict(locked.validation_summary or {})
    validation_summary["simulation"] = simulation
    validation_summary["nutrition_solver"] = solver
    validation_summary["selected_alternative_id"] = selected["alternative_id"]

    locked.current_snapshot = snapshot
    locked.proposed_payload = payload
    locked.validation_summary = validation_summary
    locked.save(update_fields=["current_snapshot", "proposed_payload", "validation_summary"])

    NutritionProposalAuditEvent.objects.create(
        proposal=locked,
        actor=user,
        action=NutritionProposalAuditEvent.ACTION_CREATED,
        status_before=locked.status,
        status_after=locked.status,
        message="Solver alternative selected for review.",
        metadata={
            "event_type": "solver_alternative_selected",
            "alternative_id": selected["alternative_id"],
            "rank": selected.get("rank"),
        },
    )
    return locked
