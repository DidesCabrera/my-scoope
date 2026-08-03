from __future__ import annotations

from dataclasses import dataclass, field


from admin_operations.viewmodel_modules.common import AdminOperationsMetricVM

@dataclass(frozen=True)
class AdminOperationsQueueVM:
    title: str
    description: str
    icon: str
    status: str
    href: str = "#"
    count: str = "0"
    priority: str = "info"
    helper: str = ""
    primary_action_label: str = "Ver cola"
    is_enabled: bool = False


@dataclass(frozen=True)
class AdminOperationsPrincipleVM:
    title: str
    description: str
    icon: str


@dataclass(frozen=True)
class AdminOperationsWarningVM:
    title: str
    domain: str
    description: str
    value: str
    severity: str = "info"
    href: str = "#"


@dataclass(frozen=True)
class AdminOperationsOverviewVM:
    title: str = "Colas accionables para operar My Scoope"
    subtitle: str = (
        "Este overview convierte señales internas en colas de trabajo staff-only. "
        "Food Catalog, Accounts, AI Assistant y Audit Log abren workflows guiados."
    )
    period_label: str = "OPS02 · Action queues"
    current_period: str = "Admin Operations V1"
    metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    queues: list[AdminOperationsQueueVM] = field(default_factory=list)
    warnings: list[AdminOperationsWarningVM] = field(default_factory=list)
    principles: list[AdminOperationsPrincipleVM] = field(default_factory=list)




__all__ = ['AdminOperationsQueueVM', 'AdminOperationsPrincipleVM', 'AdminOperationsWarningVM', 'AdminOperationsOverviewVM']
