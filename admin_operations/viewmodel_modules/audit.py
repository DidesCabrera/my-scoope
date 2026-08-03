from __future__ import annotations

from dataclasses import dataclass, field


from admin_operations.viewmodel_modules.common import AdminOperationsMetricVM

@dataclass(frozen=True)
class AdminOperationsAuditEventVM:
    pk: int
    created_label: str
    actor_label: str
    action: str
    target_label: str
    target_type: str
    target_id: str
    status_before: str
    status_after: str
    reason: str
    metadata_summary: str


@dataclass(frozen=True)
class AdminOperationsAuditLogVM:
    title: str = "Audit log operacional"
    subtitle: str = (
        "Registro append-only de acciones staff ejecutadas desde Admin Operations. "
        "Consolida trazabilidad operacional transversal sin reemplazar los ledgers de dominio."
    )
    period_label: str = "OPS06 · Operational audit log"
    current_period: str = "OPS06 · Audit Log"
    query: str = ""
    metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    events: list[AdminOperationsAuditEventVM] = field(default_factory=list)


__all__ = ['AdminOperationsAuditEventVM', 'AdminOperationsAuditLogVM']
