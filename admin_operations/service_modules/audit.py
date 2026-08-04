from __future__ import annotations

from admin_operations.models import AdminOperationAuditEvent
from admin_operations.selectors import (
    get_audit_log_payload,
)
from admin_operations.service_modules.common import (
    _format_int,
)
from admin_operations.viewmodels import (
    AdminOperationsAuditEventVM,
    AdminOperationsAuditLogVM,
    AdminOperationsMetricVM,
)


def _audit_event_to_vm(event: AdminOperationAuditEvent) -> AdminOperationsAuditEventVM:
    target_type = f"{event.target_app}.{event.target_model}"
    metadata_summary = "—"
    if isinstance(event.metadata, dict) and event.metadata:
        visible_keys = [key for key in sorted(event.metadata.keys()) if key not in {"reason"}][:4]
        metadata_summary = " · ".join(f"{key}={event.metadata.get(key)}" for key in visible_keys)
    return AdminOperationsAuditEventVM(
        pk=event.pk,
        created_label=f"{event.created_at:%Y-%m-%d %H:%M}",
        actor_label=event.actor_label or "staff",
        action=event.action,
        target_label=event.target_label or f"#{event.target_id}",
        target_type=target_type,
        target_id=event.target_id,
        status_before=event.status_before or "—",
        status_after=event.status_after or "—",
        reason=event.reason or "—",
        metadata_summary=metadata_summary,
    )


def build_audit_log_vm(*, query: str = "") -> AdminOperationsAuditLogVM:
    payload = get_audit_log_payload(query=query)
    counts = payload["counts"]
    return AdminOperationsAuditLogVM(
        query=payload["query"],
        metrics=[
            AdminOperationsMetricVM(
                label="Eventos auditados",
                value=_format_int(counts.get("total")),
                helper="Acciones staff registradas por Admin Operations.",
                icon="scroll-text",
            ),
            AdminOperationsMetricVM(
                label="Últimas 24h",
                value=_format_int(counts.get("recent_24h")),
                helper="Eventos recientes en el audit log operacional.",
                icon="clock",
            ),
            AdminOperationsMetricVM(
                label="Accounts",
                value=_format_int(counts.get("financial")),
                helper="Ajustes o releases de créditos auditados.",
                icon="credit-card",
            ),
            AdminOperationsMetricVM(
                label="AI / Propuestas",
                value=_format_int(counts.get("ai")),
                helper="Eventos IA, cuotas y propuestas auditadas.",
                icon="bot",
            ),
        ],
        events=[_audit_event_to_vm(event) for event in payload["events"]],
    )


__all__ = ['build_audit_log_vm']
