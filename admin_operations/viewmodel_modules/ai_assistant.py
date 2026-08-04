from __future__ import annotations

from dataclasses import dataclass, field

from admin_operations.viewmodel_modules.common import AdminOperationsMetricVM


@dataclass(frozen=True)
class AdminOperationsAIEventVM:
    pk: int
    created_label: str
    user_label: str
    email: str
    status: str
    action_type: str
    provider_label: str
    model_name: str
    error_type: str
    tokens_label: str
    credits_label: str
    metadata_state: str
    admin_url: str = "#"


@dataclass(frozen=True)
class AdminOperationsAIProposalVM:
    pk: int
    title: str
    source: str
    status: str
    created_label: str
    created_by_label: str
    dailyplan_label: str
    summary: str
    detail_url: str = "#"
    admin_url: str = "#"


@dataclass(frozen=True)
class AdminOperationsAIQuotaVM:
    pk: int
    user_id: int
    user_label: str
    email: str
    period: str
    plan_code: str
    usage_label: str
    daily_limit: str
    hard_blocked: bool
    admin_url: str = "#"


@dataclass(frozen=True)
class AdminOperationsAIVM:
    title: str = "Operaciones de AI Assistant"
    subtitle: str = (
        "Revisión staff-only de errores, bloqueos, propuestas AI/MCP pendientes y "
        "cuotas que pueden explicar restricciones de acceso."
    )
    period_label: str = "OPS05 · AI Assistant operations"
    current_period: str = "OPS05 · AI Assistant"
    query: str = ""
    metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    events: list[AdminOperationsAIEventVM] = field(default_factory=list)
    proposals: list[AdminOperationsAIProposalVM] = field(default_factory=list)
    quotas: list[AdminOperationsAIQuotaVM] = field(default_factory=list)





__all__ = ['AdminOperationsAIEventVM', 'AdminOperationsAIProposalVM', 'AdminOperationsAIQuotaVM', 'AdminOperationsAIVM']
