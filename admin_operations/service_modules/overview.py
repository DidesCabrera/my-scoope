from __future__ import annotations


from django.urls import reverse

from admin_operations.selectors import (
    get_operations_overview_metrics,
)
from admin_operations.viewmodels import (
    AdminOperationsMetricVM,
    AdminOperationsOverviewVM,
    AdminOperationsPrincipleVM,
    AdminOperationsQueueVM,
)
from admin_operations.models import AdminOperationAuditEvent


PRIORITY_ORDER = {"warning": 0, "watch": 1, "info": 2, "healthy": 3}


from admin_operations.service_modules.common import (
    _format_int,
    _queue_priority,
    _warning_to_vm,
)

def build_operations_overview_vm() -> AdminOperationsOverviewVM:
    metrics = get_operations_overview_metrics()
    catalog = metrics["catalog"]
    ai = metrics["ai"]
    accounts = metrics["accounts"]
    billing = metrics["billing"]

    pending_catalog_work = catalog["pending_candidates"] + catalog["catalog_foods_requiring_review"]
    ai_work = int(ai.get("total") or 0) + int(ai.get("pending_ai_proposals") or 0)
    account_work = int(accounts["wallets_with_reserved_credits"] or 0)
    billing_work = sum(int(value or 0) for value in billing.values())
    warning_count = len(metrics["warnings"])

    queues = [
        AdminOperationsQueueVM(
            title="Food Catalog",
            description="Curación de candidatos externos y alimentos master que requieren revisión antes de publicación o readiness del solver.",
            icon="database",
            status="OPS03 workflow activo",
            href=reverse("admin_operations_food_catalog"),
            count=_format_int(pending_catalog_work),
            priority=_queue_priority(pending_catalog_work),
            helper=(
                f"{_format_int(catalog['pending_candidates'])} candidatos · "
                f"{_format_int(catalog['catalog_foods_requiring_review'])} foods por revisar"
            ),
            primary_action_label="Abrir curación",
            is_enabled=True,
        ),
        AdminOperationsQueueVM(
            title="AI Assistant",
            description="Eventos IA con error/bloqueo y propuestas AI/MCP pendientes de revisión operacional.",
            icon="bot",
            status="OPS05 workflow activo",
            href=reverse("admin_operations_ai_assistant"),
            count=_format_int(ai_work),
            priority=_queue_priority(ai_work),
            helper=(
                f"{_format_int(ai.get('errors', 0))} errores · "
                f"{_format_int(ai.get('blocked', 0))} bloqueos · "
                f"{_format_int(ai.get('pending_ai_proposals', 0))} propuestas"
            ),
            primary_action_label="Revisar señales IA",
            is_enabled=True,
        ),
        AdminOperationsQueueVM(
            title="Accounts & Credits",
            description="Wallets con reservas activas y créditos retenidos que deben observarse antes de habilitar acciones financieras.",
            icon="credit-card",
            status="OPS04 workflow activo",
            href=reverse("admin_operations_accounts"),
            count=_format_int(account_work),
            priority=_queue_priority(account_work, warning_threshold=3) if account_work else "healthy",
            helper=f"{_format_int(accounts['reserved_credits_total'])} créditos reservados totales",
            primary_action_label="Revisar wallets",
            is_enabled=True,
        ),
        AdminOperationsQueueVM(
            title="Billing",
            description="Eventos fallidos, suscripciones morosas, documentos tributarios fallidos y ajustes que requieren revisión.",
            icon="receipt-text",
            status="BILL08 workflow activo",
            href=reverse("admin:billing_taxdocument_changelist"),
            count=_format_int(billing_work),
            priority=_queue_priority(billing_work),
            helper=(
                f"{_format_int(billing['failed_events'])} eventos · "
                f"{_format_int(billing['past_due_subscriptions'])} morosas · "
                f"{_format_int(billing['failed_tax_documents'])} DTE fallidos · "
                f"{_format_int(billing['tax_adjustments'])} ajustes"
            ),
            primary_action_label="Revisar Billing",
            is_enabled=True,
        ),
        AdminOperationsQueueVM(
            title="Audit Log",
            description="Registro append-only de acciones staff ejecutadas desde Admin Operations con actor, target, razón y transición.",
            icon="scroll-text",
            status="OPS06 workflow activo",
            href=reverse("admin_operations_audit_log"),
            count=_format_int(AdminOperationAuditEvent.objects.count()),
            priority="healthy",
            helper="Auditoría formal para Food Catalog, Accounts y AI.",
            primary_action_label="Ver auditoría",
            is_enabled=True,
        ),
    ]

    warnings = sorted(
        [_warning_to_vm(warning) for warning in metrics["warnings"]],
        key=lambda warning: (PRIORITY_ORDER.get(warning.severity, 99), warning.domain, warning.title),
    )

    return AdminOperationsOverviewVM(
        title="Operational Console",
        subtitle="Overview staff-only de colas accionables para convertir señales internas en flujos de resolución seguros.",
        period_label=metrics["period_label"],
        current_period="OPS06 · Audit activo",
        metrics=[
            AdminOperationsMetricVM(
                label="Trabajo operacional",
                value=_format_int(pending_catalog_work + ai_work + account_work + billing_work),
                helper="Suma de colas detectables con workflows operacionales activos.",
                icon="inbox",
            ),
            AdminOperationsMetricVM(
                label="Food Catalog",
                value=_format_int(pending_catalog_work),
                helper="Candidatos + alimentos master por revisar.",
                icon="database",
            ),
            AdminOperationsMetricVM(
                label="IA / Propuestas",
                value=_format_int(ai_work),
                helper="Errores, bloqueos y propuestas AI/MCP pendientes.",
                icon="bot",
            ),
            AdminOperationsMetricVM(
                label="Warnings activos",
                value=_format_int(warning_count),
                helper="Señales que deben orientar la priorización staff.",
                icon="triangle-alert",
            ),
        ],
        queues=queues,
        warnings=warnings,
        principles=[
            AdminOperationsPrincipleVM(
                title="Actuar, no medir",
                description="Analytics detecta señales; Operations contiene las colas y acciones guiadas para resolverlas.",
                icon="wrench",
            ),
            AdminOperationsPrincipleVM(
                title="Staff-only",
                description="Todas las rutas nacen bajo /staff/operations/ y requieren usuario autenticado con is_staff.",
                icon="shield-check",
            ),
            AdminOperationsPrincipleVM(
                title="Audit-first",
                description="Las mutaciones operacionales dejan trazabilidad append-only con actor, target, razón y transición.",
                icon="clipboard-check",
            ),
        ],
    )




__all__ = ['build_operations_overview_vm']
