from __future__ import annotations


from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from admin_operations.selectors import (
    get_ai_operations_payload,
)
from admin_operations.viewmodels import (
    AdminOperationsAIEventVM,
    AdminOperationsAIProposalVM,
    AdminOperationsAIQuotaVM,
    AdminOperationsAIVM,
    AdminOperationsMetricVM,
)
from ai_assistant.models import AICreditLedger, AIUsageEvent, AIUserCreditQuota
from notas.domain.model_modules.proposals import NutritionProposal, NutritionProposalAuditEvent


from admin_operations.service_modules.common import (
    AdminOperationResult,
    _format_int,
    _get_operation_target,
    _user_label,
    record_admin_operation_audit_event,
)

def _ai_event_to_vm(event: AIUsageEvent) -> AdminOperationsAIEventVM:
    user = event.user
    metadata_state = "Sin revisión"
    ops_meta = (event.metadata or {}).get("admin_operations") if isinstance(event.metadata, dict) else None
    if isinstance(ops_meta, dict):
        metadata_state = ops_meta.get("state") or metadata_state
    return AdminOperationsAIEventVM(
        pk=event.pk,
        created_label=f"{event.created_at:%Y-%m-%d %H:%M}",
        user_label=_user_label(user) if user else "Usuario desconocido",
        email=(getattr(user, "email", "") or getattr(user, "username", "")) if user else "—",
        status=event.status,
        action_type=event.action_type,
        provider_label=event.provider or "—",
        model_name=event.model_name or "—",
        error_type=event.error_type or "—",
        tokens_label=_format_int(event.total_tokens),
        credits_label=_format_int(event.charged_credits),
        metadata_state=metadata_state,
        admin_url=reverse("admin:ai_assistant_aiusageevent_change", args=[event.pk]),
    )


def _ai_proposal_to_vm(proposal: NutritionProposal) -> AdminOperationsAIProposalVM:
    dailyplan_label = "Sin daily plan"
    if proposal.dailyplan_id:
        dailyplan_label = getattr(proposal.dailyplan, "name", "") or f"DailyPlan #{proposal.dailyplan_id}"
    return AdminOperationsAIProposalVM(
        pk=proposal.pk,
        title=proposal.title,
        source=proposal.source,
        status=proposal.status,
        created_label=f"{proposal.created_at:%Y-%m-%d %H:%M}",
        created_by_label=_user_label(proposal.created_by),
        dailyplan_label=dailyplan_label,
        summary=(proposal.summary or "")[:220],
        detail_url=reverse("admin_operations_ai_proposal", args=[proposal.pk]),
        admin_url=reverse("admin:notas_nutritionproposal_change", args=[proposal.pk]),
    )


def _ai_quota_to_vm(quota: AIUserCreditQuota) -> AdminOperationsAIQuotaVM:
    user = quota.user
    return AdminOperationsAIQuotaVM(
        pk=quota.pk,
        user_id=user.pk,
        user_label=_user_label(user),
        email=getattr(user, "email", "") or getattr(user, "username", ""),
        period=quota.period,
        plan_code=quota.plan_code,
        usage_label=f"{_format_int(quota.credits_used)} / {_format_int(quota.monthly_credit_limit)}",
        daily_limit=_format_int(quota.daily_credit_limit),
        hard_blocked=quota.hard_blocked,
        admin_url=reverse("admin:ai_assistant_aiusercreditquota_change", args=[quota.pk]),
    )


def build_ai_operations_vm(*, query: str = "") -> AdminOperationsAIVM:
    payload = get_ai_operations_payload(query=query)
    event_counts = payload["event_counts"]
    proposal_counts = payload["proposal_counts"]
    quota_counts = payload["quota_counts"]
    total_work = int(event_counts.get("total") or 0) + int(proposal_counts.get("total") or 0) + int(quota_counts.get("total") or 0)

    return AdminOperationsAIVM(
        query=payload["query"],
        metrics=[
            AdminOperationsMetricVM(
                label="Trabajo AI",
                value=_format_int(total_work),
                helper="Eventos IA recientes + propuestas pendientes + cuotas con bloqueo/saturación.",
                icon="bot",
            ),
            AdminOperationsMetricVM(
                label="Eventos IA",
                value=_format_int(event_counts.get("total")),
                helper=f"{_format_int(event_counts.get('errors'))} errores · {_format_int(event_counts.get('blocked'))} bloqueos en últimos 7 días.",
                icon="triangle-alert",
            ),
            AdminOperationsMetricVM(
                label="Propuestas",
                value=_format_int(proposal_counts.get("total")),
                helper=f"{_format_int(proposal_counts.get('ai'))} AI · {_format_int(proposal_counts.get('mcp'))} MCP pendientes.",
                icon="clipboard-check",
            ),
            AdminOperationsMetricVM(
                label="Cuotas",
                value=_format_int(quota_counts.get("total")),
                helper=f"{_format_int(quota_counts.get('hard_blocked'))} hard-blocked o sobre límite mensual.",
                icon="shield-alert",
            ),
        ],
        events=[_ai_event_to_vm(event) for event in payload["events"]],
        proposals=[_ai_proposal_to_vm(proposal) for proposal in payload["proposals"]],
        quotas=[_ai_quota_to_vm(quota) for quota in payload["quotas"]],
    )


def perform_ai_usage_event_operation(*, event_id: int, action: str, actor, reason: str) -> AdminOperationResult:
    reason = (reason or "").strip()
    if not reason:
        return AdminOperationResult(ok=False, message="La razón es obligatoria para revisar un evento IA.")
    if action not in {"acknowledge", "escalate"}:
        raise ValidationError(f"Unknown AI usage event operation: {action}")

    event = _get_operation_target(AIUsageEvent, pk=event_id)
    actor_label = getattr(actor, "email", "") or getattr(actor, "username", "staff") or "staff"
    metadata = dict(event.metadata or {})
    ops_meta = metadata.get("admin_operations") if isinstance(metadata, dict) else None
    metadata["admin_operations"] = {
        "source": "OPS05",
        "state": "acknowledged" if action == "acknowledge" else "escalated",
        "reason": reason,
        "actor": actor_label,
        "actor_id": getattr(actor, "pk", None),
        "reviewed_at": timezone.now().isoformat(),
    }
    old_state = ops_meta.get("state") if isinstance(ops_meta, dict) else "unreviewed"
    new_state = metadata["admin_operations"]["state"]
    event.metadata = metadata
    event.save(update_fields=["metadata"])
    record_admin_operation_audit_event(
        actor=actor,
        action=f"ai_assistant.usage_event.{action}",
        target=event,
        reason=reason,
        status_before=old_state or "unreviewed",
        status_after=new_state,
        metadata={"source_patch": "OPS05", "event_status": event.status, "action_type": event.action_type},
    )
    label = "Evento IA reconocido" if action == "acknowledge" else "Evento IA escalado"
    return AdminOperationResult(ok=True, message=f"{label}: {event.action_type}.")


def perform_ai_quota_operation(*, quota_id: int, action: str, actor, reason: str) -> AdminOperationResult:
    reason = (reason or "").strip()
    if not reason:
        return AdminOperationResult(ok=False, message="La razón es obligatoria para bloquear o desbloquear acceso IA.")
    if action not in {"block", "unblock"}:
        raise ValidationError(f"Unknown AI quota operation: {action}")

    quota = _get_operation_target(AIUserCreditQuota.objects.select_related("user"), pk=quota_id)
    target_blocked = action == "block"
    if quota.hard_blocked == target_blocked:
        state = "bloqueada" if target_blocked else "desbloqueada"
        return AdminOperationResult(ok=False, message=f"La cuota ya está {state}.")

    actor_label = getattr(actor, "email", "") or getattr(actor, "username", "staff") or "staff"
    old_blocked = quota.hard_blocked
    quota.hard_blocked = target_blocked
    quota.save(update_fields=["hard_blocked", "updated_at"])
    ledger = AICreditLedger.objects.create(
        user=quota.user,
        period=quota.period,
        plan_code=quota.plan_code,
        action_type="admin_operations.ai_quota_block" if target_blocked else "admin_operations.ai_quota_unblock",
        kind=AICreditLedger.Kind.ADJUSTMENT,
        credits=0,
        reason=reason,
        metadata={"actor": actor_label, "actor_id": getattr(actor, "pk", None), "source": "OPS05"},
    )
    record_admin_operation_audit_event(
        actor=actor,
        action="ai_assistant.quota.block" if target_blocked else "ai_assistant.quota.unblock",
        target=quota,
        reason=reason,
        status_before=f"hard_blocked={old_blocked}",
        status_after=f"hard_blocked={quota.hard_blocked}",
        metadata={"source_patch": "OPS05", "ledger_id": ledger.pk, "period": quota.period, "plan_code": quota.plan_code},
    )
    return AdminOperationResult(ok=True, message="Acceso IA bloqueado." if target_blocked else "Acceso IA desbloqueado.")


def build_ai_proposal_detail_vm(proposal_id: int) -> AdminOperationsAIProposalVM:
    proposal = _get_operation_target(
        NutritionProposal.objects.select_related("created_by", "dailyplan"),
        pk=proposal_id,
        source__in=[NutritionProposal.SOURCE_AI, NutritionProposal.SOURCE_MCP],
    )
    return _ai_proposal_to_vm(proposal)


def perform_ai_proposal_operation(*, proposal_id: int, action: str, actor, reason: str) -> AdminOperationResult:
    reason = (reason or "").strip()
    if not reason:
        return AdminOperationResult(ok=False, message="La razón es obligatoria para aprobar o rechazar una propuesta IA.")
    if action not in {"approve", "reject"}:
        raise ValidationError(f"Unknown AI proposal operation: {action}")

    proposal = _get_operation_target(
        NutritionProposal.objects.select_related("created_by", "dailyplan"),
        pk=proposal_id,
        source__in=[NutritionProposal.SOURCE_AI, NutritionProposal.SOURCE_MCP],
    )
    if proposal.status != NutritionProposal.STATUS_PENDING_REVIEW:
        return AdminOperationResult(ok=False, message="La propuesta ya no está pendiente de revisión.")

    status_before = proposal.status
    proposal.status = NutritionProposal.STATUS_APPROVED if action == "approve" else NutritionProposal.STATUS_REJECTED
    proposal.reviewed_by = actor if getattr(actor, "is_authenticated", False) else None
    proposal.reviewed_at = timezone.now()
    proposal.save(update_fields=["status", "reviewed_by", "reviewed_at"])

    audit_action = (
        NutritionProposalAuditEvent.ACTION_APPROVED
        if action == "approve"
        else NutritionProposalAuditEvent.ACTION_REJECTED
    )
    proposal_audit = NutritionProposalAuditEvent.objects.create(
        proposal=proposal,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=audit_action,
        status_before=status_before,
        status_after=proposal.status,
        message=f"Admin Operations OPS05: {reason}",
        metadata={"source": "OPS05", "reason": reason},
    )
    record_admin_operation_audit_event(
        actor=actor,
        action="notas.nutrition_proposal.approve" if action == "approve" else "notas.nutrition_proposal.reject",
        target=proposal,
        reason=reason,
        status_before=status_before,
        status_after=proposal.status,
        metadata={"source_patch": "OPS05", "proposal_audit_event_id": proposal_audit.pk, "proposal_source": proposal.source},
    )
    return AdminOperationResult(
        ok=True,
        message="Propuesta IA aprobada." if action == "approve" else "Propuesta IA rechazada.",
    )




__all__ = ['build_ai_operations_vm', 'perform_ai_usage_event_operation', 'perform_ai_quota_operation', 'build_ai_proposal_detail_vm', 'perform_ai_proposal_operation']
