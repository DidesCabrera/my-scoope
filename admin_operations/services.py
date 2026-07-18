from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import tempfile
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from admin_operations.selectors import (
    get_account_detail_payload,
    get_accounts_operations_payload,
    get_audit_log_payload,
    get_ai_operations_payload,
    get_food_catalog_inventory_payload,
    get_food_catalog_import_batches_payload,
    get_food_catalog_operations_payload,
    get_operations_overview_metrics,
)
from admin_operations.viewmodels import (
    AdminOperationsAIEventVM,
    AdminOperationsAIProposalVM,
    AdminOperationsAIQuotaVM,
    AdminOperationsAIVM,
    AdminOperationsAuditEventVM,
    AdminOperationsAuditLogVM,
    AdminOperationsCandidateDetailVM,
    AdminOperationsCandidateVM,
    AdminOperationsCatalogCoverageVM,
    AdminOperationsCatalogInventoryFoodVM,
    AdminOperationsCatalogInventoryVM,
    AdminOperationsCatalogImportBatchVM,
    AdminOperationsCatalogImportsVM,
    AdminOperationsAccountDetailVM,
    AdminOperationsAccountsVM,
    AdminOperationsCatalogFoodVM,
    AdminOperationsCreditLedgerVM,
    AdminOperationsCreditReservationVM,
    AdminOperationsCreditWalletVM,
    AdminOperationsFoodCatalogVM,
    AdminOperationsMetricVM,
    AdminOperationsOverviewVM,
    AdminOperationsPrincipleVM,
    AdminOperationsQueueVM,
    AdminOperationsWarningVM,
)
from accounts.models import AccountSubscription, CreditLedger, CreditWallet
from ai_assistant.models import AICreditLedger, AIUsageEvent, AIUserCreditQuota
from accounts.services.credits import current_account_credit_period, release_account_credit_reservation
from food_catalog.application.curation import transition_catalog_food_status
from food_catalog.models import CatalogCurationCandidate, CatalogFood, CatalogImportBatch, CatalogImportSourcePolicy
from food_catalog.infrastructure.core_natural_foods_seed import (
    apply_core_natural_foods_seed,
    core_natural_foods_seed_identity,
    dry_run_core_natural_foods_seed,
)
from food_catalog.infrastructure.imports.governance import (
    CatalogImportGovernanceError,
    catalog_import_identity,
    record_catalog_import_dry_run,
)
from food_catalog.application.imports.usda.foundation_foods_reader import (
    FoundationFoodsReaderError,
    extract_foundation_food_payloads,
)
from food_catalog.infrastructure.imports.catalog_import import CATALOG_SOURCE_NAME_USDA
from food_catalog.infrastructure.imports.usda_catalog_import import (
    dry_run_usda_catalog_food_payloads,
    import_usda_catalog_food_payloads,
)
from food_catalog.application.brand_intake import (
    apply_brand_food_intake_csv,
    brand_food_intake_identity,
    dry_run_brand_food_intake_csv,
)
from food_catalog.application.manual_intake import (
    apply_manual_evidence_csv,
    dry_run_manual_evidence_csv,
    manual_evidence_identity,
)
from notas.application.services.commands.food_catalog_backfill import (
    DEFAULT_OPERATIONAL_BACKFILL_SOURCE_VERSION,
    OPERATIONAL_BACKFILL_SOURCE_NAME,
    OperationalFoodCatalogBackfillError,
    backfill_catalog_from_operational_foods,
    dry_run_backfill_catalog_from_operational_foods,
    operational_backfill_identity,
)
from notas.domain.model_modules.proposals import NutritionProposal, NutritionProposalAuditEvent
from admin_operations.models import AdminOperationAuditEvent


PRIORITY_ORDER = {"warning": 0, "watch": 1, "info": 2, "healthy": 3}

CANDIDATE_ACTIONS = {
    "start_review": (
        CatalogCurationCandidate.STATUS_IN_REVIEW,
        "Marcar en revisión",
        "Candidate moved to in review",
    ),
    "approve": (
        CatalogCurationCandidate.STATUS_APPROVED_FOR_CURATION,
        "Aprobar para curación",
        "Candidate approved for curation",
    ),
    "needs_more_evidence": (
        CatalogCurationCandidate.STATUS_NEEDS_MORE_EVIDENCE,
        "Pedir más evidencia",
        "Candidate marked as needing more evidence",
    ),
    "reject": (
        CatalogCurationCandidate.STATUS_REJECTED,
        "Rechazar",
        "Candidate rejected",
    ),
}

CATALOG_FOOD_ACTIONS = {
    "pending_review": (CatalogFood.STATUS_PENDING_REVIEW, "Enviar a revisión"),
    "reviewed": (CatalogFood.STATUS_REVIEWED, "Marcar revisado"),
    "verified": (CatalogFood.STATUS_VERIFIED, "Marcar verificado"),
    "needs_more_evidence": (CatalogFood.STATUS_NEEDS_MORE_EVIDENCE, "Pedir más evidencia"),
    "rejected": (CatalogFood.STATUS_REJECTED, "Rechazar"),
}


@dataclass(frozen=True)
class AdminOperationResult:
    ok: bool
    message: str


def _actor_label(actor) -> str:
    return getattr(actor, "email", "") or getattr(actor, "username", "staff") or "staff"


def record_admin_operation_audit_event(
    *,
    actor,
    action: str,
    target,
    reason: str,
    status_before: str = "",
    status_after: str = "",
    metadata: dict | None = None,
) -> AdminOperationAuditEvent:
    target_meta = getattr(target, "_meta", None)
    target_label = str(target)[:220] if target is not None else ""
    return AdminOperationAuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        actor_label=_actor_label(actor),
        action=action,
        source="OPS06",
        target_app=getattr(target_meta, "app_label", "unknown"),
        target_model=getattr(target_meta, "model_name", target.__class__.__name__ if target is not None else "unknown"),
        target_id=str(getattr(target, "pk", "")),
        target_label=target_label,
        status_before=str(status_before or ""),
        status_after=str(status_after or ""),
        reason=(reason or "").strip(),
        metadata=metadata or {},
    )


def _format_int(value) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def _format_decimal(value: Decimal | None, *, suffix: str = "") -> str:
    if value is None:
        return "—"
    rendered = format(Decimal(value), "f").rstrip("0").rstrip(".") or "0"
    return f"{rendered}{suffix}"


def _queue_priority(count: int, *, warning_threshold: int = 1) -> str:
    return "warning" if int(count or 0) >= warning_threshold else "healthy"


def _warning_to_vm(warning: dict) -> AdminOperationsWarningVM:
    return AdminOperationsWarningVM(
        title=warning["title"],
        domain=warning["domain"],
        description=warning["description"],
        value=_format_int(warning["value"]),
        severity=warning.get("severity", "info"),
    )


def build_operations_overview_vm() -> AdminOperationsOverviewVM:
    metrics = get_operations_overview_metrics()
    catalog = metrics["catalog"]
    ai = metrics["ai"]
    accounts = metrics["accounts"]

    pending_catalog_work = catalog["pending_candidates"] + catalog["catalog_foods_requiring_review"]
    ai_work = int(ai.get("total") or 0) + int(ai.get("pending_ai_proposals") or 0)
    account_work = int(accounts["wallets_with_reserved_credits"] or 0)
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
                value=_format_int(pending_catalog_work + ai_work + account_work),
                helper="Suma inicial de colas detectables con workflows Food Catalog, Accounts y AI activos.",
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


def _candidate_to_vm(candidate: CatalogCurationCandidate) -> AdminOperationsCandidateVM:
    reviewed_label = "Sin revisión"
    if candidate.reviewed_by_id and candidate.reviewed_at:
        reviewed_label = f"{candidate.reviewed_by} · {candidate.reviewed_at:%Y-%m-%d %H:%M}"
    elif candidate.reviewed_at:
        reviewed_label = f"Revisado · {candidate.reviewed_at:%Y-%m-%d %H:%M}"

    return AdminOperationsCandidateVM(
        pk=candidate.pk,
        title=candidate.display_name,
        brand_name=candidate.brand_name,
        provider=candidate.provider,
        status=candidate.status,
        reason=candidate.reason,
        priority=candidate.priority,
        demand_label=(
            f"vistos {candidate.seen_count_at_creation} · "
            f"seleccionados {candidate.selected_count_at_creation}"
        ),
        source_url=candidate.source_url,
        detail_url=reverse("admin_operations_food_catalog_candidate", args=[candidate.pk]),
        admin_url=reverse("admin:food_catalog_catalogcurationcandidate_change", args=[candidate.pk]),
        notes=candidate.notes,
        reviewed_label=reviewed_label,
    )


def _catalog_food_to_vm(catalog_food: CatalogFood) -> AdminOperationsCatalogFoodVM:
    return AdminOperationsCatalogFoodVM(
        pk=catalog_food.pk,
        title=catalog_food.display_name,
        brand_name=catalog_food.brand_name,
        status=catalog_food.status,
        source_type=catalog_food.source_type,
        quality_score=catalog_food.data_quality_score,
        solver_enabled=catalog_food.solver_enabled,
        macro_label=(
            f"P {_format_decimal(catalog_food.protein_g_per_100g, suffix='g')} · "
            f"C {_format_decimal(catalog_food.carbs_g_per_100g, suffix='g')} · "
            f"F {_format_decimal(catalog_food.fat_g_per_100g, suffix='g')}"
        ),
        admin_url=reverse("admin:food_catalog_catalogfood_change", args=[catalog_food.pk]),
    )


def build_food_catalog_operations_vm() -> AdminOperationsFoodCatalogVM:
    payload = get_food_catalog_operations_payload()
    candidate_counts = payload["candidate_counts"]
    food_counts = payload["food_counts"]
    total_work = int(candidate_counts["total"] or 0) + int(food_counts["total"] or 0)

    return AdminOperationsFoodCatalogVM(
        metrics=[
            AdminOperationsMetricVM(
                label="Trabajo Food Catalog",
                value=_format_int(total_work),
                helper="Candidatos + alimentos master dentro de estados accionables.",
                icon="database",
            ),
            AdminOperationsMetricVM(
                label="Candidatos",
                value=_format_int(candidate_counts["total"]),
                helper=f"{_format_int(candidate_counts['high_priority'])} alta prioridad · {_format_int(candidate_counts['needs_more_evidence'])} necesitan evidencia.",
                icon="list-checks",
            ),
            AdminOperationsMetricVM(
                label="Foods por revisar",
                value=_format_int(food_counts["total"]),
                helper=f"{_format_int(food_counts['pending_review'])} pending review · {_format_int(food_counts['needs_more_evidence'])} necesitan evidencia.",
                icon="wheat",
            ),
            AdminOperationsMetricVM(
                label="Mutaciones OPS03",
                value="guiadas",
                helper="Candidatos con razón obligatoria; foods master por workflow existente.",
                icon="shield-check",
            ),
        ],
        candidates=[_candidate_to_vm(candidate) for candidate in payload["candidates"]],
        catalog_foods=[_catalog_food_to_vm(catalog_food) for catalog_food in payload["catalog_foods"]],
    )


def build_food_catalog_inventory_vm(
    *,
    query: str = "",
    status: str = "",
    source_type: str = "",
    food_group: str = "",
    solver_state: str = "",
    page: int | str = 1,
) -> AdminOperationsCatalogInventoryVM:
    payload = get_food_catalog_inventory_payload(
        query=query,
        status=status,
        source_type=source_type,
        food_group=food_group,
        solver_state=solver_state,
        page=page,
    )
    aggregate = payload["aggregate"]
    total = int(aggregate["total"] or 0)
    page_obj = payload["page_obj"]

    category_coverage = [
        AdminOperationsCatalogCoverageVM(
            label=row["label"],
            total=_format_int(row["total"]),
            share_label=_format_share(row["total"], total),
            helper=(
                f"{_format_int(row['published'])} publicados · "
                f"{_format_int(row['solver_enabled'])} habilitados para solver"
                if row["key"] != "unmapped"
                else "Requiere normalizar food_group para entrar en una categoría comparable."
            ),
        )
        for row in payload["category_coverage"]
    ]

    source_labels = dict(CatalogFood.SOURCE_TYPE_CHOICES)
    source_coverage = [
        AdminOperationsCatalogCoverageVM(
            label=source_labels.get(row["source_type"], row["source_type"] or "Sin fuente"),
            total=_format_int(row["total"]),
            share_label=_format_share(row["total"], total),
            helper=(
                f"{_format_int(row['published'])} publicados · "
                f"calidad promedio {_format_average(row['average_quality'])}/100"
            ),
        )
        for row in payload["source_breakdown"]
    ]

    filter_params = {
        "q": payload["query"],
        "status": payload["status"],
        "source": payload["source_type"],
        "group": payload["food_group"],
        "solver": payload["solver_state"],
    }

    return AdminOperationsCatalogInventoryVM(
        query=payload["query"],
        selected_status=payload["status"],
        selected_source=payload["source_type"],
        selected_group=payload["food_group"],
        selected_solver_state=payload["solver_state"],
        metrics=[
            AdminOperationsMetricVM(
                label="Alimentos persistidos",
                value=_format_int(total),
                helper="Todos los CatalogFood, sin limitar por estado.",
                icon="database",
            ),
            AdminOperationsMetricVM(
                label="Publicados",
                value=_format_int(aggregate["published"]),
                helper=_format_share(aggregate["published"], total),
                icon="badge-check",
            ),
            AdminOperationsMetricVM(
                label="Habilitados para solver",
                value=_format_int(aggregate["solver_enabled"]),
                helper=_format_share(aggregate["solver_enabled"], total),
                icon="calculator",
            ),
            AdminOperationsMetricVM(
                label="Calidad promedio",
                value=f"{_format_average(aggregate['average_quality'])}/100",
                helper="Promedio del data_quality_score persistido.",
                icon="scan-search",
            ),
        ],
        nutrition_metrics=[
            AdminOperationsMetricVM(
                label="Proteína promedio",
                value=f"{_format_average(aggregate['average_protein'])} g",
                helper="Promedio descriptivo por 100 g del catálogo; no es una meta dietaria.",
                icon="drumstick",
            ),
            AdminOperationsMetricVM(
                label="Carbohidratos promedio",
                value=f"{_format_average(aggregate['average_carbs'])} g",
                helper="Promedio descriptivo por 100 g del catálogo.",
                icon="wheat",
            ),
            AdminOperationsMetricVM(
                label="Grasa promedio",
                value=f"{_format_average(aggregate['average_fat'])} g",
                helper="Promedio descriptivo por 100 g del catálogo.",
                icon="droplets",
            ),
            AdminOperationsMetricVM(
                label="Fibra promedio conocida",
                value=f"{_format_average(aggregate['average_fiber'])} g",
                helper="Sólo considera registros donde fiber_g_per_100g está informado.",
                icon="sprout",
            ),
        ],
        gap_metrics=[
            AdminOperationsMetricVM(
                label="Sin grupo alimentario",
                value=_format_int(aggregate["missing_group"]),
                helper=_format_share(aggregate["missing_group"], total),
                icon="tag",
            ),
            AdminOperationsMetricVM(
                label="Sin evidencia asociada",
                value=_format_int(aggregate["without_evidence"]),
                helper="CatalogFood sin filas CatalogFoodSource.",
                icon="file-question",
            ),
            AdminOperationsMetricVM(
                label="Nutrición extendida incompleta",
                value=_format_int(aggregate["incomplete_extended_nutrition"]),
                helper="Falta al menos kcal, fibra, azúcar, grasa saturada o sodio.",
                icon="list-x",
            ),
            AdminOperationsMetricVM(
                label="Semántica culinaria desconocida",
                value=_format_int(aggregate["unknown_culinary_semantics"]),
                helper="preparation_state o food_form permanece en unknown.",
                icon="circle-help",
            ),
        ],
        category_coverage=category_coverage,
        source_coverage=source_coverage,
        foods=[_catalog_inventory_food_to_vm(food) for food in page_obj.object_list],
        status_options=list(payload["status_options"]),
        source_options=list(payload["source_options"]),
        group_options=list(payload["group_options"]),
        filtered_total=_format_int(payload["filtered_total"]),
        page_label=f"Página {page_obj.number} de {page_obj.paginator.num_pages}",
        previous_url=_inventory_page_url(filter_params, page_obj.previous_page_number()) if page_obj.has_previous() else "",
        next_url=_inventory_page_url(filter_params, page_obj.next_page_number()) if page_obj.has_next() else "",
    )


def build_food_catalog_imports_vm(*, source_type: str = "", status: str = "") -> AdminOperationsCatalogImportsVM:
    payload = get_food_catalog_import_batches_payload(source_type=source_type, status=status)
    aggregate = payload["aggregate"]
    source_labels = dict(CatalogFood.SOURCE_TYPE_CHOICES)

    return AdminOperationsCatalogImportsVM(
        selected_source=payload["source_type"],
        selected_status=payload["status"],
        metrics=[
            AdminOperationsMetricVM("Ejecuciones", _format_int(aggregate["total"]), "Dry-runs e imports persistidos.", "history"),
            AdminOperationsMetricVM("Dry-runs", _format_int(aggregate["dry_runs"]), "Planes no mutantes trazables.", "scan-search"),
            AdminOperationsMetricVM("Imports", _format_int(aggregate["imports"]), "Batches de aplicación.", "database-zap"),
            AdminOperationsMetricVM(
                "Applies sin dry-run",
                _format_int(payload["orphan_applies"]),
                "Las filas históricas pueden carecer de correlación; toda ejecución FCG nueva debe ser 0.",
                "triangle-alert",
            ),
        ],
        batches=[
            AdminOperationsCatalogImportBatchVM(
                pk=batch.pk,
                run_type="Dry-run" if batch.is_dry_run else "Import",
                source_label=f"{source_labels.get(batch.source_type, batch.source_type)} · {batch.source_name}",
                status=batch.status,
                version=batch.source_version or "—",
                counts_label=(
                    f"total {batch.total_rows} · importables/importados {batch.imported_rows} · "
                    f"omitidos {batch.skipped_rows} · fallidos {batch.failed_rows}"
                ),
                operator_label=_actor_label(batch.requested_by) if batch.requested_by else "sistema/legacy",
                reason=batch.reason or batch.notes or "—",
                input_hash_label=f"{batch.input_sha256[:12]}…" if batch.input_sha256 else "legacy/sin hash",
                dry_run_label=(
                    f"dry-run #{batch.dry_run_batch_id}" if batch.dry_run_batch_id else ("plan" if batch.is_dry_run else "sin correlación")
                ),
                started_label=batch.started_at.strftime("%Y-%m-%d %H:%M"),
            )
            for batch in payload["batches"]
        ],
        source_options=list(payload["source_options"]),
        status_options=list(payload["status_options"]),
    )


def perform_core_seed_dry_run(*, actor, reason: str) -> AdminOperationResult:
    normalized_reason = (reason or "").strip()
    if not normalized_reason:
        return AdminOperationResult(False, "Debes indicar una razón operacional.")

    plan = dry_run_core_natural_foods_seed()
    if plan.validation_errors:
        return AdminOperationResult(False, "El seed interno no superó su validación.")
    batch = record_catalog_import_dry_run(
        identity=core_natural_foods_seed_identity(),
        total_rows=plan.total_rows,
        would_import_rows=plan.to_create + plan.to_update,
        skipped_rows=plan.invalid_rows,
        failed_rows=0,
        requested_by=actor,
        reason=normalized_reason,
        summary_payload={"to_create": plan.to_create, "to_update": plan.to_update, "invalid": plan.invalid_rows},
    )
    record_admin_operation_audit_event(
        actor=actor,
        action="food_catalog.core_seed.dry_run",
        target=batch,
        reason=normalized_reason,
        status_after=batch.status,
        metadata={"total": plan.total_rows, "to_create": plan.to_create, "to_update": plan.to_update},
    )
    return AdminOperationResult(
        True,
        f"Dry-run #{batch.pk}: total={plan.total_rows}, crear={plan.to_create}, actualizar={plan.to_update}.",
    )


def perform_core_seed_apply(*, actor, dry_run_batch_id: str, reason: str) -> AdminOperationResult:
    normalized_reason = (reason or "").strip()
    if not normalized_reason:
        return AdminOperationResult(False, "Debes indicar una razón operacional.")
    try:
        dry_run_batch = CatalogImportBatch.objects.get(pk=int(dry_run_batch_id))
        result = apply_core_natural_foods_seed(
            dry_run_batch=dry_run_batch,
            requested_by=actor,
            reason=normalized_reason,
        )
    except (ValueError, TypeError, CatalogImportBatch.DoesNotExist, CatalogImportGovernanceError) as exc:
        return AdminOperationResult(False, f"No se pudo aplicar el seed: {exc}")

    record_admin_operation_audit_event(
        actor=actor,
        action="food_catalog.core_seed.apply",
        target=result.batch,
        reason=normalized_reason,
        status_before=f"dry_run={dry_run_batch.pk}",
        status_after=result.batch.status,
        metadata={"created": result.created_rows, "updated": result.updated_rows, "published": 0},
    )
    return AdminOperationResult(
        True,
        f"Seed aplicado en batch #{result.batch.pk}: creados={result.created_rows}, actualizados={result.updated_rows}, publicados=0.",
    )


def perform_usda_dry_run(
    *, actor, upload, source_version: str, source_dataset: str, limit: str, reason: str
) -> AdminOperationResult:
    try:
        payloads, identity, normalized_limit = _prepare_usda_upload(
            upload=upload,
            source_version=source_version,
            source_dataset=source_dataset,
            limit=limit,
        )
        result = dry_run_usda_catalog_food_payloads(
            payloads=payloads,
            source_version=source_version,
            source_dataset=source_dataset,
        )
        batch = record_catalog_import_dry_run(
            identity=identity,
            total_rows=result.total_rows,
            would_import_rows=result.would_import_rows,
            skipped_rows=result.skipped_rows,
            failed_rows=result.failed_rows,
            requested_by=actor,
            reason=reason,
            summary_payload={"reason_counts": result.reason_counts, "limit": normalized_limit},
        )
    except (ValueError, TypeError, json.JSONDecodeError, FoundationFoodsReaderError, CatalogImportGovernanceError) as exc:
        return AdminOperationResult(False, f"No se pudo validar USDA: {exc}")

    record_admin_operation_audit_event(
        actor=actor,
        action="food_catalog.usda.dry_run",
        target=batch,
        reason=reason,
        status_after=batch.status,
        metadata={"total": result.total_rows, "would_import": result.would_import_rows},
    )
    return AdminOperationResult(True, f"USDA dry-run #{batch.pk}: importables={result.would_import_rows}/{result.total_rows}.")


def perform_usda_apply(
    *, actor, upload, source_version: str, source_dataset: str, limit: str, dry_run_batch_id: str, reason: str
) -> AdminOperationResult:
    try:
        payloads, identity, _normalized_limit = _prepare_usda_upload(
            upload=upload,
            source_version=source_version,
            source_dataset=source_dataset,
            limit=limit,
        )
        dry_run_batch = CatalogImportBatch.objects.get(pk=int(dry_run_batch_id))
        result = import_usda_catalog_food_payloads(
            payloads=payloads,
            source_version=source_version,
            source_dataset=source_dataset,
            identity=identity,
            dry_run_batch=dry_run_batch,
            requested_by=actor,
            reason=reason,
        )
    except (
        ValueError,
        TypeError,
        json.JSONDecodeError,
        FoundationFoodsReaderError,
        CatalogImportGovernanceError,
        CatalogImportBatch.DoesNotExist,
    ) as exc:
        return AdminOperationResult(False, f"No se pudo importar USDA: {exc}")

    record_admin_operation_audit_event(
        actor=actor,
        action="food_catalog.usda.apply",
        target=result.batch,
        reason=reason,
        status_before=f"dry_run={dry_run_batch.pk}",
        status_after=result.batch.status,
        metadata={"imported": result.imported_rows, "skipped": result.skipped_rows, "failed": result.failed_rows},
    )
    return AdminOperationResult(True, f"USDA batch #{result.batch.pk}: importados={result.imported_rows}, omitidos={result.skipped_rows}.")


def _prepare_usda_upload(*, upload, source_version: str, source_dataset: str, limit: str):
    if upload is None:
        raise ValueError("Debes adjuntar un JSON USDA.")
    normalized_version = (source_version or "").strip()
    if not normalized_version:
        raise ValueError("La versión USDA es obligatoria.")
    normalized_dataset = (source_dataset or "foundation_foods").strip()
    normalized_limit = int(limit)
    if normalized_limit < 1 or normalized_limit > 10:
        raise ValueError("La muestra USDA debe contener entre 1 y 10 filas.")
    raw_bytes = upload.read()
    decoded = json.loads(raw_bytes.decode("utf-8"))
    payloads = extract_foundation_food_payloads(decoded)[:normalized_limit]
    identity = catalog_import_identity(
        source_type=CatalogFood.SOURCE_USDA,
        source_name=CATALOG_SOURCE_NAME_USDA,
        source_version=normalized_version,
        input_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        parameters_payload={"source_dataset": normalized_dataset, "limit": normalized_limit},
    )
    return payloads, identity, normalized_limit


def perform_brand_dry_run(*, actor, upload, limit: str, reason: str) -> AdminOperationResult:
    try:
        normalized_limit = _brand_limit(limit)
        with _uploaded_temp_file(upload, suffix=".csv") as path:
            result = dry_run_brand_food_intake_csv(path, limit=normalized_limit)
            batch = record_catalog_import_dry_run(
                identity=brand_food_intake_identity(path, limit=normalized_limit),
                total_rows=result.total_rows,
                would_import_rows=result.total_rows - result.skipped_rows,
                skipped_rows=result.skipped_rows,
                failed_rows=0,
                requested_by=actor,
                reason=reason,
                summary_payload={"errors": result.errors},
            )
    except (ValueError, OSError, CatalogImportGovernanceError) as exc:
        return AdminOperationResult(False, f"No se pudo validar marcas: {exc}")
    if result.errors:
        return AdminOperationResult(False, f"Dry-run #{batch.pk} bloqueado: {'; '.join(result.errors[:3])}")
    record_admin_operation_audit_event(
        actor=actor,
        action="food_catalog.brand.dry_run",
        target=batch,
        reason=reason,
        status_after=batch.status,
        metadata={"total": result.total_rows},
    )
    return AdminOperationResult(True, f"Marcas dry-run #{batch.pk}: {result.total_rows} filas válidas.")


def perform_brand_apply(*, actor, upload, limit: str, dry_run_batch_id: str, reason: str) -> AdminOperationResult:
    try:
        normalized_limit = _brand_limit(limit)
        dry_run_batch = CatalogImportBatch.objects.get(pk=int(dry_run_batch_id))
        with _uploaded_temp_file(upload, suffix=".csv") as path:
            result = apply_brand_food_intake_csv(
                path,
                dry_run_batch=dry_run_batch,
                reason=reason,
                limit=normalized_limit,
                created_by=actor,
            )
    except (ValueError, TypeError, OSError, CatalogImportBatch.DoesNotExist, CatalogImportGovernanceError) as exc:
        return AdminOperationResult(False, f"No se pudo importar marcas: {exc}")
    if result.errors:
        return AdminOperationResult(False, f"Import bloqueado: {'; '.join(result.errors[:3])}")
    batch = result.batch
    assert batch is not None
    record_admin_operation_audit_event(
        actor=actor,
        action="food_catalog.brand.apply",
        target=batch,
        reason=reason,
        status_before=f"dry_run={dry_run_batch.pk}",
        status_after=batch.status,
        metadata={"created": result.created_rows, "updated": result.updated_rows},
    )
    return AdminOperationResult(True, f"Marcas batch #{batch.pk}: creados={result.created_rows}, actualizados={result.updated_rows}.")


def _brand_limit(value: str) -> int:
    normalized = int(value)
    if normalized < 1 or normalized > 5:
        raise ValueError("La muestra de marcas debe contener entre 1 y 5 filas.")
    return normalized


class _uploaded_temp_file:
    def __init__(self, upload, *, suffix: str):
        if upload is None:
            raise ValueError("Debes adjuntar un archivo.")
        self.upload = upload
        self.suffix = suffix
        self.file = None

    def __enter__(self):
        self.file = tempfile.NamedTemporaryFile(suffix=self.suffix)
        self.file.write(self.upload.read())
        self.file.flush()
        return self.file.name

    def __exit__(self, exc_type, exc, traceback):
        self.file.close()


def perform_manual_dry_run(*, actor, upload, limit: str, reason: str) -> AdminOperationResult:
    try:
        normalized_limit = _brand_limit(limit)
        with _uploaded_temp_file(upload, suffix=".csv") as path:
            plan = dry_run_manual_evidence_csv(path, limit=normalized_limit)
            versions = {row.source_version for row in plan.rows}
            if len(versions) != 1:
                raise ValueError("La muestra debe tener una única source_version y filas válidas.")
            batch = record_catalog_import_dry_run(
                identity=manual_evidence_identity(path, limit=normalized_limit, source_version=next(iter(versions))),
                total_rows=plan.total_rows,
                would_import_rows=plan.valid_rows,
                skipped_rows=plan.invalid_rows,
                failed_rows=0,
                requested_by=actor,
                reason=reason,
                summary_payload={"errors": plan.errors},
            )
    except (ValueError, OSError, CatalogImportGovernanceError) as exc:
        return AdminOperationResult(False, f"No se pudo validar curación manual: {exc}")
    if plan.errors:
        return AdminOperationResult(False, f"Dry-run #{batch.pk} bloqueado: {'; '.join(plan.errors[:3])}")
    record_admin_operation_audit_event(actor=actor, action="food_catalog.manual.dry_run", target=batch, reason=reason, status_after=batch.status)
    return AdminOperationResult(True, f"Curación manual dry-run #{batch.pk}: {plan.valid_rows}/{plan.total_rows} válidas.")


def perform_manual_apply(*, actor, upload, limit: str, dry_run_batch_id: str, reason: str) -> AdminOperationResult:
    try:
        normalized_limit = _brand_limit(limit)
        dry_run = CatalogImportBatch.objects.get(pk=int(dry_run_batch_id))
        with _uploaded_temp_file(upload, suffix=".csv") as path:
            result = apply_manual_evidence_csv(
                path,
                limit=normalized_limit,
                dry_run_batch=dry_run,
                reason=reason,
                requested_by=actor,
            )
    except (ValueError, TypeError, OSError, CatalogImportBatch.DoesNotExist, CatalogImportGovernanceError) as exc:
        return AdminOperationResult(False, f"No se pudo importar curación manual: {exc}")
    record_admin_operation_audit_event(
        actor=actor,
        action="food_catalog.manual.apply",
        target=result.batch,
        reason=reason,
        status_before=f"dry_run={dry_run.pk}",
        status_after=result.batch.status,
        metadata={"created": result.created_rows, "updated": result.updated_rows},
    )
    return AdminOperationResult(True, f"Curación manual batch #{result.batch.pk}: creados={result.created_rows}, actualizados={result.updated_rows}.")


def perform_backfill_dry_run(*, actor, limit: str, reason: str) -> AdminOperationResult:
    try:
        normalized_limit = int(limit)
        if normalized_limit < 1 or normalized_limit > 10:
            raise ValueError("El límite de backfill debe estar entre 1 y 10.")
        result = dry_run_backfill_catalog_from_operational_foods(limit=normalized_limit, sample_size=5)
        batch = record_catalog_import_dry_run(
            identity=operational_backfill_identity(
                source_name=OPERATIONAL_BACKFILL_SOURCE_NAME,
                source_version=DEFAULT_OPERATIONAL_BACKFILL_SOURCE_VERSION,
                limit=normalized_limit,
                status=CatalogFood.STATUS_REVIEWED,
            ),
            total_rows=result.total_rows,
            would_import_rows=result.created_rows,
            skipped_rows=result.skipped_rows,
            failed_rows=result.failed_rows,
            requested_by=actor,
            reason=reason,
            summary_payload={"reason_counts": result.reason_counts},
        )
    except (ValueError, OperationalFoodCatalogBackfillError, CatalogImportGovernanceError) as exc:
        return AdminOperationResult(False, f"No se pudo validar backfill: {exc}")
    record_admin_operation_audit_event(actor=actor, action="food_catalog.backfill.dry_run", target=batch, reason=reason, status_after=batch.status)
    return AdminOperationResult(True, f"Backfill dry-run #{batch.pk}: elegibles={result.created_rows}, inspeccionados={result.total_rows}.")


def perform_backfill_apply(*, actor, limit: str, dry_run_batch_id: str, reason: str) -> AdminOperationResult:
    try:
        normalized_limit = int(limit)
        if normalized_limit < 1 or normalized_limit > 10:
            raise ValueError("El límite de backfill debe estar entre 1 y 10.")
        dry_run = CatalogImportBatch.objects.get(pk=int(dry_run_batch_id))
        result = backfill_catalog_from_operational_foods(
            limit=normalized_limit,
            dry_run_batch=dry_run,
            requested_by=actor,
            reason=reason,
        )
    except (ValueError, TypeError, CatalogImportBatch.DoesNotExist, OperationalFoodCatalogBackfillError, CatalogImportGovernanceError) as exc:
        return AdminOperationResult(False, f"No se pudo ejecutar backfill: {exc}")
    assert result.batch is not None
    record_admin_operation_audit_event(
        actor=actor,
        action="food_catalog.backfill.apply",
        target=result.batch,
        reason=reason,
        status_before=f"dry_run={dry_run.pk}",
        status_after=result.batch.status,
        metadata={"created": result.created_rows, "skipped": result.skipped_rows},
    )
    return AdminOperationResult(True, f"Backfill batch #{result.batch.pk}: creados={result.created_rows}, omitidos={result.skipped_rows}.")


def perform_import_source_policy_operation(
    *, actor, source_type: str, source_name: str, max_batch_rows: str, action: str, reason: str
) -> AdminOperationResult:
    normalized_reason = (reason or "").strip()
    normalized_name = (source_name or "").strip()
    if not normalized_reason or not normalized_name:
        return AdminOperationResult(False, "Fuente y razón operacional son obligatorias.")
    if source_type not in dict(CatalogFood.SOURCE_TYPE_CHOICES) or source_type in {
        CatalogFood.SOURCE_OPEN_FOOD_FACTS,
        CatalogFood.SOURCE_FATSECRET,
    }:
        return AdminOperationResult(False, "La fuente no es escalable en FCG.")
    try:
        maximum = int(max_batch_rows)
    except (TypeError, ValueError):
        return AdminOperationResult(False, "El máximo del batch debe ser numérico.")
    if maximum < 1 or maximum > 500:
        return AdminOperationResult(False, "El máximo debe estar entre 1 y 500.")

    policy, _created = CatalogImportSourcePolicy.objects.get_or_create(
        source_type=source_type,
        source_name=normalized_name,
    )
    before = f"approved={policy.scale_approved},kill={policy.kill_switch},max={policy.max_batch_rows}"
    if action == "approve":
        policy.scale_approved = True
        policy.kill_switch = False
        policy.is_enabled = True
        policy.max_batch_rows = maximum
        policy.approved_by = actor
        policy.approved_at = timezone.now()
        policy.approval_reason = normalized_reason
    elif action == "kill":
        policy.kill_switch = True
        policy.approval_reason = normalized_reason
    else:
        return AdminOperationResult(False, "Acción de política desconocida.")
    policy.save()
    after = f"approved={policy.scale_approved},kill={policy.kill_switch},max={policy.max_batch_rows}"
    record_admin_operation_audit_event(
        actor=actor,
        action=f"food_catalog.import_policy.{action}",
        target=policy,
        reason=normalized_reason,
        status_before=before,
        status_after=after,
    )
    return AdminOperationResult(True, f"Política {normalized_name}: {after}.")


def _catalog_inventory_food_to_vm(catalog_food: CatalogFood) -> AdminOperationsCatalogInventoryFoodVM:
    sources = list(catalog_food.sources.all())
    portions = list(catalog_food.portions.all())
    aliases = list(catalog_food.aliases.all())
    source_lines = [
        " · ".join(
            part
            for part in [
                source.source_name,
                source.source_type,
                f"ID {source.source_food_id}" if source.source_food_id else "",
                f"dataset {source.source_dataset}" if source.source_dataset else "",
                f"v{source.source_version}" if source.source_version else "",
                f"licencia {source.license_status}",
            ]
            if part
        )
        for source in sources
    ]
    portion_lines = [
        f"{portion.label}: {_format_decimal(portion.grams, suffix=' g')}"
        f"{' (default)' if portion.is_default else ''}"
        for portion in portions
    ]
    alias_lines = [
        f"{alias.name} ({alias.alias_type}, {alias.language}{f'-{alias.country}' if alias.country else ''})"
        for alias in aliases
    ]

    quality_flags = []
    if not catalog_food.food_group:
        quality_flags.append("sin food_group")
    if not sources:
        quality_flags.append("sin evidencia")
    if catalog_food.preparation_state == CatalogFood.PREPARATION_UNKNOWN:
        quality_flags.append("preparación unknown")
    if catalog_food.food_form == CatalogFood.FOOD_FORM_UNKNOWN:
        quality_flags.append("food_form unknown")
    if any(
        value is None
        for value in [
            catalog_food.calories_kcal_per_100g,
            catalog_food.fiber_g_per_100g,
            catalog_food.sugar_g_per_100g,
            catalog_food.saturated_fat_g_per_100g,
            catalog_food.sodium_mg_per_100g,
        ]
    ):
        quality_flags.append("nutrición extendida incompleta")

    return AdminOperationsCatalogInventoryFoodVM(
        pk=catalog_food.pk,
        title=catalog_food.display_name,
        identity_lines=[
            f"ID {catalog_food.pk} · ref {catalog_food.catalog_ref}",
            f"canonical: {catalog_food.canonical_name or '—'}",
            f"marca: {catalog_food.brand_name or '—'} · branded: {'sí' if catalog_food.is_branded else 'no'}",
            f"versión {catalog_food.catalog_version} · {catalog_food.language or '—'} · país {catalog_food.country or '—'}",
        ],
        classification_lines=[
            f"grupo: {catalog_food.food_group or '—'}",
            f"subgrupo: {catalog_food.food_subgroup or '—'}",
            f"forma: {catalog_food.food_form} · preparación: {catalog_food.preparation_state}",
            f"esfuerzo: {catalog_food.preparation_effort} · costo: {catalog_food.cost_band}",
        ],
        governance_lines=[
            f"origen: {catalog_food.source_type}",
            f"estado: {catalog_food.status}",
            *(source_lines or ["evidencia: —"]),
        ],
        nutrition_lines=[
            f"P {_format_decimal(catalog_food.protein_g_per_100g, suffix=' g')} · C {_format_decimal(catalog_food.carbs_g_per_100g, suffix=' g')} · F {_format_decimal(catalog_food.fat_g_per_100g, suffix=' g')}",
            f"kcal {_format_decimal(catalog_food.calories_kcal_per_100g)} · macro-kcal {_format_decimal(catalog_food.macro_calories_kcal)}",
            f"fibra {_format_decimal(catalog_food.fiber_g_per_100g, suffix=' g')} · azúcar {_format_decimal(catalog_food.sugar_g_per_100g, suffix=' g')}",
            f"saturada {_format_decimal(catalog_food.saturated_fat_g_per_100g, suffix=' g')} · sodio {_format_decimal(catalog_food.sodium_mg_per_100g, suffix=' mg')}",
        ],
        functional_lines=[
            f"roles: {_format_labels(catalog_food.functional_roles)}",
            f"afinidades: {_format_labels(catalog_food.meal_affinities)}",
            f"dietary: {_format_labels(catalog_food.dietary_tags)}",
            f"alérgenos: {_format_labels(catalog_food.allergens)}",
        ],
        solver_lines=[
            f"enabled: {'sí' if catalog_food.solver_enabled else 'no'}",
            f"rango: {_format_decimal(catalog_food.solver_min_portion_g, suffix=' g')} – {_format_decimal(catalog_food.solver_max_portion_g, suffix=' g')} · paso {_format_decimal(catalog_food.solver_portion_step_g, suffix=' g')}",
            f"capabilities: {catalog_food.solver_capabilities_version}",
            f"confianza features: {_format_mapping(catalog_food.solver_feature_confidence)}",
        ],
        quality_lines=[
            f"data quality: {catalog_food.data_quality_score}/100",
            f"confidence: {_format_decimal(catalog_food.confidence_score, suffix='/100')}",
            f"brechas: {', '.join(quality_flags) if quality_flags else 'sin brechas base detectadas'}",
        ],
        relation_lines=[
            f"fuentes: {len(sources)} · porciones: {len(portions)} · aliases: {len(aliases)}",
            *(portion_lines or ["porciones (0): —"]),
            *(alias_lines or ["aliases (0): —"]),
        ],
        lifecycle_lines=[
            f"creado: {catalog_food.created_at:%Y-%m-%d %H:%M} · {_user_label(catalog_food.created_by) if catalog_food.created_by else 'sistema'}",
            f"revisado: {catalog_food.reviewed_at:%Y-%m-%d %H:%M} · {_user_label(catalog_food.reviewed_by) if catalog_food.reviewed_by else '—'}" if catalog_food.reviewed_at else "revisado: —",
            f"publicado: {catalog_food.published_at:%Y-%m-%d %H:%M}" if catalog_food.published_at else "publicado: —",
            f"actualizado: {catalog_food.updated_at:%Y-%m-%d %H:%M}",
        ],
        admin_url=reverse("admin:food_catalog_catalogfood_change", args=[catalog_food.pk]),
    )


def _format_average(value) -> str:
    if value is None:
        return "—"
    return f"{Decimal(value):.1f}"


def _format_share(value, total: int) -> str:
    if not total:
        return "0% del catálogo"
    return f"{(int(value or 0) / total) * 100:.1f}% del catálogo"


def _format_labels(values) -> str:
    if not values:
        return "—"
    return ", ".join(str(value) for value in values)


def _format_mapping(values) -> str:
    if not values:
        return "—"
    return ", ".join(f"{key}={value}" for key, value in sorted(values.items()))


def _inventory_page_url(params: dict[str, str], page: int) -> str:
    clean_params = {key: value for key, value in params.items() if value}
    clean_params["page"] = str(page)
    return f"{reverse('admin_operations_food_catalog_inventory')}?{urlencode(clean_params)}"


def build_candidate_detail_vm(candidate_id: int) -> AdminOperationsCandidateDetailVM:
    candidate = get_object_or_404(
        CatalogCurationCandidate.objects.select_related("reviewed_by"),
        pk=candidate_id,
    )
    return AdminOperationsCandidateDetailVM(
        title=f"Candidato · {candidate.display_name}",
        subtitle="Revisión guiada con razón obligatoria para dejar contexto operacional antes del audit log formal OPS06.",
        candidate=_candidate_to_vm(candidate),
        allowed_actions=[
            (key, label)
            for key, (_status, label, _message) in CANDIDATE_ACTIONS.items()
            if candidate.status != _status
        ],
    )


def perform_candidate_operation(*, candidate_id: int, action: str, actor, reason: str) -> AdminOperationResult:
    reason = (reason or "").strip()
    if not reason:
        return AdminOperationResult(ok=False, message="La razón es obligatoria para intervenir un candidato.")

    if action not in CANDIDATE_ACTIONS:
        raise ValidationError(f"Unknown candidate operation: {action}")

    candidate = get_object_or_404(CatalogCurationCandidate, pk=candidate_id)
    target_status, _label, success_message = CANDIDATE_ACTIONS[action]
    old_status = candidate.status

    if old_status == target_status:
        return AdminOperationResult(ok=False, message="El candidato ya está en ese estado.")

    timestamp = timezone.now()
    actor_label = getattr(actor, "email", "") or getattr(actor, "username", "staff") or "staff"
    note_line = (
        f"[{timestamp:%Y-%m-%d %H:%M}] Admin Operations · {actor_label}: "
        f"{old_status} → {target_status}. Razón: {reason}"
    )

    candidate.status = target_status
    candidate.reviewed_at = timestamp
    if getattr(actor, "is_authenticated", False):
        candidate.reviewed_by = actor
    candidate.notes = f"{candidate.notes}\n{note_line}".strip()
    candidate.save(update_fields=["status", "reviewed_at", "reviewed_by", "notes", "updated_at"])
    record_admin_operation_audit_event(
        actor=actor,
        action=f"food_catalog.candidate.{action}",
        target=candidate,
        reason=reason,
        status_before=old_status,
        status_after=target_status,
        metadata={"source_patch": "OPS03", "candidate_provider": candidate.provider},
    )

    return AdminOperationResult(ok=True, message=success_message)


def perform_catalog_food_operation(*, catalog_food_id: int, action: str, actor, reason: str) -> AdminOperationResult:
    reason = (reason or "").strip()
    if not reason:
        return AdminOperationResult(ok=False, message="La razón es obligatoria para intervenir un alimento master.")

    if action not in CATALOG_FOOD_ACTIONS:
        raise ValidationError(f"Unknown catalog food operation: {action}")

    catalog_food = get_object_or_404(CatalogFood.objects.prefetch_related("sources", "portions"), pk=catalog_food_id)
    old_status = catalog_food.status
    target_status, label = CATALOG_FOOD_ACTIONS[action]
    result = transition_catalog_food_status(catalog_food, target_status, user=actor)

    if result.errors:
        return AdminOperationResult(ok=False, message="; ".join(result.errors))
    if not result.changed:
        return AdminOperationResult(ok=False, message="El alimento master ya está en ese estado.")
    catalog_food.refresh_from_db(fields=["status", "updated_at"])
    record_admin_operation_audit_event(
        actor=actor,
        action=f"food_catalog.catalog_food.{action}",
        target=catalog_food,
        reason=reason,
        status_before=old_status,
        status_after=catalog_food.status,
        metadata={"source_patch": "OPS03", "target_status": target_status},
    )

    return AdminOperationResult(ok=True, message=f"{label}: {catalog_food.display_name}")


def flash_operation_result(request, result: AdminOperationResult) -> None:
    if result.ok:
        messages.success(request, result.message)
    else:
        messages.warning(request, result.message)



def _user_label(user) -> str:
    full_name = (getattr(user, "get_full_name", lambda: "")() or "").strip()
    return full_name or getattr(user, "email", "") or getattr(user, "username", "") or f"User #{user.pk}"


def _subscription_label(subscription: AccountSubscription | None) -> str:
    if subscription is None:
        return "Sin suscripción activa"
    plan_label = getattr(subscription.plan, "slug", "") or getattr(subscription.plan, "name", "") or "plan"
    return f"{plan_label} · {subscription.status}"


def _wallet_to_vm(wallet: CreditWallet, *, subscription: AccountSubscription | None = None) -> AdminOperationsCreditWalletVM:
    user = wallet.user
    return AdminOperationsCreditWalletVM(
        user_id=user.pk,
        user_label=_user_label(user),
        email=getattr(user, "email", "") or getattr(user, "username", ""),
        balance=_format_int(wallet.balance),
        reserved_balance=_format_int(wallet.reserved_balance),
        available_credits=_format_int(wallet.available_credits),
        period=wallet.period or "—",
        plan_snapshot_code=wallet.plan_snapshot_code or "—",
        subscription_label=_subscription_label(subscription),
        detail_url=reverse("admin_operations_account_detail", args=[user.pk]),
        admin_url=reverse("admin:accounts_creditwallet_change", args=[wallet.pk]),
        has_reserved_credits=wallet.has_reserved_credits,
    )


def _reservation_to_vm(reservation: CreditLedger) -> AdminOperationsCreditReservationVM:
    user = reservation.user
    reference_label = " · ".join(part for part in [reservation.reference_type, reservation.reference_id] if part) or "Sin referencia"
    return AdminOperationsCreditReservationVM(
        pk=reservation.pk,
        user_id=user.pk,
        user_label=_user_label(user),
        email=getattr(user, "email", "") or getattr(user, "username", ""),
        credits=_format_int(reservation.reserved_delta),
        reference_type=reservation.reference_type,
        reference_id=reservation.reference_id,
        reference_label=reference_label,
        created_label=f"{reservation.created_at:%Y-%m-%d %H:%M}",
        reason=reservation.reason,
        detail_url=reverse("admin_operations_account_detail", args=[user.pk]),
    )


def _ledger_to_vm(entry: CreditLedger) -> AdminOperationsCreditLedgerVM:
    reference_label = " · ".join(part for part in [entry.reference_type, entry.reference_id] if part) or "—"
    return AdminOperationsCreditLedgerVM(
        pk=entry.pk,
        created_label=f"{entry.created_at:%Y-%m-%d %H:%M}",
        kind=entry.kind,
        credits_delta=f"{int(entry.credits_delta or 0):+d}",
        reserved_delta=f"{int(entry.reserved_delta or 0):+d}",
        balance_after=_format_int(entry.balance_after),
        reserved_balance_after=_format_int(entry.reserved_balance_after),
        reference_label=reference_label,
        reason=entry.reason or "—",
    )


def build_accounts_operations_vm(*, query: str = "") -> AdminOperationsAccountsVM:
    payload = get_accounts_operations_payload(query=query)
    wallet_counts = payload["wallet_counts"]
    reservation_counts = payload["reservation_counts"]
    subscriptions_by_user = payload["subscriptions_by_user"]
    total_work = int(wallet_counts.get("with_reserved") or 0) + int(reservation_counts.get("total") or 0)

    return AdminOperationsAccountsVM(
        query=payload["query"],
        metrics=[
            AdminOperationsMetricVM(
                label="Trabajo Accounts",
                value=_format_int(total_work),
                helper="Wallets con reservas + reservas abiertas accionables.",
                icon="credit-card",
            ),
            AdminOperationsMetricVM(
                label="Wallets",
                value=_format_int(wallet_counts.get("total")),
                helper=f"{_format_int(wallet_counts.get('with_reserved'))} con créditos reservados.",
                icon="wallet-cards",
            ),
            AdminOperationsMetricVM(
                label="Reservas abiertas",
                value=_format_int(reservation_counts.get("total")),
                helper=f"{_format_int(reservation_counts.get('reserved_total'))} créditos retenidos por reservas no cerradas.",
                icon="lock-keyhole",
            ),
            AdminOperationsMetricVM(
                label="Mutaciones OPS04",
                value="ledger",
                helper="Ajustes y releases siempre agregan CreditLedger con razón obligatoria.",
                icon="shield-check",
            ),
        ],
        wallets=[
            _wallet_to_vm(wallet, subscription=subscriptions_by_user.get(wallet.user_id))
            for wallet in payload["wallets"]
        ],
        reservations=[_reservation_to_vm(reservation) for reservation in payload["reservations"]],
    )


def build_account_detail_vm(user_id: int) -> AdminOperationsAccountDetailVM:
    payload = get_account_detail_payload(user_id=user_id)
    user = payload["user"]
    wallet = payload["wallet"]
    if wallet is None:
        wallet = CreditWallet.objects.create(
            user=user,
            balance=0,
            reserved_balance=0,
            period=current_account_credit_period(),
        )
    return AdminOperationsAccountDetailVM(
        title=f"Cuenta · {_user_label(user)}",
        subtitle="Revisión staff-only de wallet, ledger append-only, reservas abiertas y ajustes manuales con razón obligatoria.",
        wallet=_wallet_to_vm(wallet, subscription=payload["subscription"]),
        ledger_entries=[_ledger_to_vm(entry) for entry in payload["ledger_entries"]],
        reservations=[_reservation_to_vm(reservation) for reservation in payload["reservations"]],
    )


def perform_credit_adjustment(*, user_id: int, actor, credits_delta: str, reason: str) -> AdminOperationResult:
    reason = (reason or "").strip()
    if not reason:
        return AdminOperationResult(ok=False, message="La razón es obligatoria para ajustar créditos.")
    try:
        delta = int(str(credits_delta or "").strip())
    except (TypeError, ValueError):
        return AdminOperationResult(ok=False, message="El ajuste debe ser un número entero de créditos.")
    if delta == 0:
        return AdminOperationResult(ok=False, message="El ajuste debe ser distinto de cero.")

    User = get_user_model()
    target_user = get_object_or_404(User, pk=user_id)
    actor_label = getattr(actor, "email", "") or getattr(actor, "username", "staff") or "staff"

    with transaction.atomic():
        wallet, _created = CreditWallet.objects.select_for_update().get_or_create(
            user=target_user,
            defaults={"balance": 0, "reserved_balance": 0, "period": current_account_credit_period()},
        )
        old_balance = int(wallet.balance or 0)
        old_reserved_balance = int(wallet.reserved_balance or 0)
        new_balance = old_balance + delta
        if new_balance < 0:
            return AdminOperationResult(ok=False, message="El ajuste no puede dejar balance negativo.")
        if new_balance < int(wallet.reserved_balance or 0):
            return AdminOperationResult(ok=False, message="El ajuste no puede dejar balance menor que los créditos reservados.")
        wallet.balance = new_balance
        wallet.save(update_fields=["balance", "updated_at"])
        ledger = CreditLedger.objects.create(
            wallet=wallet,
            user=target_user,
            kind=CreditLedger.Kind.ADJUSTMENT,
            credits_delta=delta,
            reserved_delta=0,
            balance_after=wallet.balance,
            reserved_balance_after=wallet.reserved_balance,
            period=wallet.period,
            plan_snapshot_code=wallet.plan_snapshot_code,
            reference_type="admin_operations.credit_adjustment",
            reference_id=str(actor.pk) if getattr(actor, "pk", None) else "staff",
            reason=reason,
            metadata={"actor": actor_label, "source": "OPS04"},
        )
        record_admin_operation_audit_event(
            actor=actor,
            action="accounts.credit.adjustment",
            target=wallet,
            reason=reason,
            status_before=f"balance={old_balance};reserved={old_reserved_balance}",
            status_after=f"balance={wallet.balance};reserved={wallet.reserved_balance}",
            metadata={"source_patch": "OPS04", "ledger_id": ledger.pk, "credits_delta": delta, "target_user_id": target_user.pk},
        )
    return AdminOperationResult(ok=True, message=f"Ajuste registrado en ledger #{ledger.pk} ({delta:+d} créditos).")


def perform_credit_reservation_release(*, reservation_id: int, actor, reason: str) -> AdminOperationResult:
    reason = (reason or "").strip()
    if not reason:
        return AdminOperationResult(ok=False, message="La razón es obligatoria para liberar una reserva.")
    reservation = get_object_or_404(
        CreditLedger.objects.select_related("wallet", "user"),
        pk=reservation_id,
        kind=CreditLedger.Kind.RESERVE,
    )
    if reservation.reserved_delta <= 0:
        return AdminOperationResult(ok=False, message="La reserva no tiene créditos retenidos.")
    closed = CreditLedger.objects.filter(
        kind__in=(CreditLedger.Kind.CONSUME, CreditLedger.Kind.RELEASE),
        reference_type=reservation.reference_type,
        reference_id=reservation.reference_id,
    ).exists()
    if closed:
        return AdminOperationResult(ok=False, message="La reserva ya fue cerrada anteriormente.")

    actor_label = getattr(actor, "email", "") or getattr(actor, "username", "staff") or "staff"
    result = release_account_credit_reservation(
        user=reservation.user,
        reference_type=reservation.reference_type,
        reference_id=reservation.reference_id,
        reason=reason,
        metadata={"actor": actor_label, "source": "OPS04", "released_by_staff": True},
    )
    if not result.get("released"):
        return AdminOperationResult(ok=False, message=f"No se pudo liberar la reserva: {result.get('reason', 'unknown')}.")
    reservation.wallet.refresh_from_db(fields=["balance", "reserved_balance", "updated_at"])
    record_admin_operation_audit_event(
        actor=actor,
        action="accounts.credit.reservation_release",
        target=reservation,
        reason=reason,
        status_before=f"reserved_delta={reservation.reserved_delta}",
        status_after=f"released={result.get('released')};wallet_reserved={reservation.wallet.reserved_balance}",
        metadata={
            "source_patch": "OPS04",
            "released_credits": result.get("credits"),
            "reference_type": reservation.reference_type,
            "reference_id": reservation.reference_id,
            "wallet_id": reservation.wallet_id,
        },
    )
    return AdminOperationResult(ok=True, message=f"Reserva liberada: {_format_int(result.get('credits'))} créditos.")


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

    event = get_object_or_404(AIUsageEvent, pk=event_id)
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

    quota = get_object_or_404(AIUserCreditQuota.objects.select_related("user"), pk=quota_id)
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
    proposal = get_object_or_404(
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

    proposal = get_object_or_404(
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
