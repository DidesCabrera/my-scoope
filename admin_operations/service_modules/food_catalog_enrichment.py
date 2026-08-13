"""Viewmodel and operations for governed Food Catalog imports and readiness."""

from collections import defaultdict

from django.urls import reverse

from admin_operations.selector_modules.food_catalog import get_food_catalog_import_batches_payload
from admin_operations.service_modules.common import (
    AdminOperationResult,
    _actor_label,
    _format_int,
    _get_operation_target,
    record_admin_operation_audit_event,
)
from admin_operations.viewmodels import (
    AdminOperationsCatalogEnrichmentBatchVM,
    AdminOperationsCatalogImportBatchVM,
    AdminOperationsCatalogImportsVM,
    AdminOperationsMetricVM,
    AdminOperationsReadinessBatchDetailVM,
    AdminOperationsReadinessBatchVM,
    AdminOperationsReadinessFoodVM,
    AdminOperationsReadinessProposalGroupVM,
    AdminOperationsReadinessProposalVM,
    AdminOperationsReadinessVM,
)
from food_catalog.application.readiness_pipeline import READINESS_POLICY_VERSION
from food_catalog.infrastructure.enrichment import (
    CatalogEnrichmentError,
    apply_enrichment_batch,
    revert_enrichment_batch,
)
from food_catalog.infrastructure.readiness_audit import audit_catalog_readiness
from food_catalog.infrastructure.readiness_pipeline import (
    prepare_readiness_batch,
    readiness_incomplete_queryset,
)
from food_catalog.infrastructure.source_portion_backfill import (
    backfill_source_portions,
    source_portion_backfill_candidates,
)
from food_catalog.models import CatalogEnrichmentBatch, CatalogFood, CatalogFoodSource


def build_catalog_enrichment_batch_vms(*, limit: int = 50) -> list[AdminOperationsCatalogEnrichmentBatchVM]:
    return [
        AdminOperationsCatalogEnrichmentBatchVM(
            batch_ref=str(batch.batch_ref),
            environment=batch.environment,
            status=batch.status,
            counts_label=(
                f"propuestas {batch.total_proposals} · válidas {batch.valid_proposals} · "
                f"aplicadas {batch.applied_proposals} · fallidas {batch.failed_proposals}"
            ),
            reason=batch.reason,
            contract_label=f"{batch.contract_version} · {batch.policy_version}",
            created_label=batch.created_at.strftime("%Y-%m-%d %H:%M"),
        )
        for batch in CatalogEnrichmentBatch.objects.order_by("-created_at")[:limit]
    ]


def build_food_catalog_readiness_vm(*, limit: int = 100) -> AdminOperationsReadinessVM:
    audit = audit_catalog_readiness()
    incomplete_rows = {row["catalog_food_id"]: row for row in audit.foods if row["missing_fields"]}
    foods = CatalogFood.objects.filter(pk__in=incomplete_rows).order_by("id")[:limit]
    batches = CatalogEnrichmentBatch.objects.filter(
        policy_version=READINESS_POLICY_VERSION,
    ).order_by("-created_at")[:50]
    return AdminOperationsReadinessVM(
        metrics=[
            AdminOperationsMetricVM("Con fuente confiable", _format_int(audit.source_complete), "Elegibles para completar internamente.", "badge-check"),
            AdminOperationsMetricVM("Completos", _format_int(audit.internally_complete), "Sin campos internos obligatorios pendientes.", "circle-check"),
            AdminOperationsMetricVM("Pendientes", _format_int(audit.internally_incomplete), "Alimentos que necesitan propuestas.", "list-todo"),
            AdminOperationsMetricVM("Perfiles inválidos", _format_int(len(audit.invalid_solver_food_ids)), "Rangos o requisitos del solver inconsistentes.", "triangle-alert"),
        ],
        foods=[
            AdminOperationsReadinessFoodVM(
                pk=food.pk,
                title=food.display_name,
                status_label=food.get_status_display(),
                source_label=_source_label(incomplete_rows[food.pk]["source"]),
                missing_label=", ".join(incomplete_rows[food.pk]["missing_fields"]),
                detail_url=reverse("admin_operations_food_catalog_food", args=[food.pk]),
            )
            for food in foods
        ],
        batches=[_batch_vm(batch) for batch in batches],
        audit_passes=audit.passes,
        source_backfill_pending=len(source_portion_backfill_candidates()),
    )


def build_readiness_batch_detail_vm(batch_ref: str) -> AdminOperationsReadinessBatchDetailVM:
    batch = _get_operation_target(
        CatalogEnrichmentBatch.objects.filter(policy_version=READINESS_POLICY_VERSION),
        batch_ref=batch_ref,
    )
    grouped = defaultdict(list)
    proposals = batch.proposals.select_related("catalog_food").prefetch_related(
        "catalog_food__sources"
    ).order_by("catalog_food_id", "field_name")
    for proposal in proposals:
        grouped[proposal.catalog_food_id].append(proposal)
    groups = []
    for food_proposals in grouped.values():
        food = food_proposals[0].catalog_food
        source = _trusted_source(food)
        groups.append(AdminOperationsReadinessProposalGroupVM(
            food_pk=food.pk,
            title=food.display_name,
            status_label=food.get_status_display(),
            source_label=(f"{source.source_name} · {source.source_food_id}" if source else "Sin fuente confiable"),
            source_url=source.source_url if source else "",
            food_detail_url=reverse("admin_operations_food_catalog_food", args=[food.pk]),
            proposals=[AdminOperationsReadinessProposalVM(
                field_label=proposal.field_name,
                current_label=_value_label(proposal.current_value),
                proposed_label=_value_label(proposal.proposed_value),
                policy_label=proposal.policy_version,
                confidence_label=f"{proposal.confidence}%",
                rationale=proposal.rationale,
                evidence=list(proposal.evidence_references),
            ) for proposal in food_proposals],
        ))
    return AdminOperationsReadinessBatchDetailVM(
        title=f"Lote {batch.batch_ref}",
        subtitle="Revisión agrupada por alimento antes de aplicar cualquier cambio interno.",
        batch_ref=str(batch.batch_ref),
        status=batch.status,
        environment=batch.environment,
        reason=batch.reason,
        counts_label=(
            f"{batch.total_proposals} propuestas · {batch.valid_proposals} válidas · "
            f"{batch.applied_proposals} aplicadas · {batch.failed_proposals} inválidas"
        ),
        manifest_hash_label=batch.manifest_sha256,
        groups=groups,
        action_url=reverse("admin_operations_food_catalog_readiness_batch_action", args=[batch.batch_ref]),
        can_apply=batch.status == CatalogEnrichmentBatch.STATUS_DRY_RUN_VALID,
        can_revert=batch.status == CatalogEnrichmentBatch.STATUS_APPLIED,
    )


def prepare_catalog_readiness_operation(*, actor, food_ids, environment: str, reason: str):
    try:
        ids = _parse_food_ids(food_ids)
    except ValueError as exc:
        return AdminOperationResult(False, str(exc)), None
    if not 1 <= len(ids) <= 10:
        return AdminOperationResult(False, "Selecciona entre 1 y 10 alimentos."), None
    if environment not in {"staging", "production"} or not (reason or "").strip():
        return AdminOperationResult(False, "Ambiente y motivo son obligatorios."), None
    foods = list(readiness_incomplete_queryset().filter(
        pk__in=ids,
        status__in=(CatalogFood.STATUS_MANUAL_CANDIDATE, CatalogFood.STATUS_PENDING_REVIEW),
    ).order_by("id"))
    if len(foods) != len(ids):
        return AdminOperationResult(
            False,
            "La selección contiene alimentos ya completos, sin fuente confiable o fuera del estado permitido.",
        ), None
    try:
        batch, result, skipped = prepare_readiness_batch(
            foods=foods,
            environment=environment,
            reason=reason,
            requested_by=actor,
        )
    except (ValueError, CatalogEnrichmentError) as exc:
        return AdminOperationResult(False, str(exc)), None
    record_admin_operation_audit_event(
        actor=actor,
        action="food_catalog.readiness.prepare",
        target=batch,
        reason=reason,
        status_before="none",
        status_after=batch.status,
        metadata={"food_ids": ids, "valid": result.valid, "invalid": result.invalid, "skipped": skipped},
    )
    return AdminOperationResult(
        True,
        f"Lote preparado con {result.valid} propuestas válidas. No se modificaron ni publicaron alimentos.",
    ), str(batch.batch_ref)


def perform_catalog_readiness_batch_operation(*, batch_ref: str, action: str, actor, reason: str):
    batch = _get_operation_target(
        CatalogEnrichmentBatch.objects.filter(policy_version=READINESS_POLICY_VERSION),
        batch_ref=batch_ref,
    )
    before = batch.status
    try:
        if action == "apply":
            apply_enrichment_batch(
                batch=batch, manifest=batch.manifest_payload, actor=actor, reason=reason,
            )
            message = f"Lote aplicado: {batch.applied_proposals} cambios; 0 publicaciones; 0 snapshots."
        elif action == "revert":
            revert_enrichment_batch(batch=batch, actor=actor, reason=reason)
            message = "Lote revertido de forma segura."
        else:
            return AdminOperationResult(False, "Acción de readiness no soportada.")
    except CatalogEnrichmentError as exc:
        return AdminOperationResult(False, str(exc))
    record_admin_operation_audit_event(
        actor=actor,
        action=f"food_catalog.readiness.{action}",
        target=batch,
        reason=reason,
        status_before=before,
        status_after=batch.status,
        metadata={"manifest_sha256": batch.manifest_sha256, "applied_proposals": batch.applied_proposals},
    )
    return AdminOperationResult(True, message)


def perform_source_portion_backfill_operation(
    *, actor, apply: bool, reason: str, limit=10, after_id=0
) -> AdminOperationResult:
    try:
        parsed_limit = int(limit)
        parsed_after = int(after_id or 0)
        result = backfill_source_portions(
            limit=parsed_limit, after_id=parsed_after, apply=apply, reason=reason,
        )
    except (TypeError, ValueError) as exc:
        return AdminOperationResult(False, str(exc))
    target = CatalogFoodSource.objects.filter(pk=result.rows[0]["source_id"]).first() if result.rows else None
    record_admin_operation_audit_event(
        actor=actor,
        action=f"food_catalog.source_portions.{'apply' if apply else 'dry_run'}",
        target=target,
        reason=reason,
        status_before="missing_source_portions",
        status_after="source_portions_recorded" if apply else "dry_run_only",
        metadata={
            "batch_ref": result.batch_ref,
            "source_ids": [row["source_id"] for row in result.rows],
            "proposed": result.proposed,
            "applied": result.applied,
            "remaining": result.remaining,
            "next_after_id": result.next_after_id,
        },
    )
    verb = "aplicadas" if apply else "detectadas"
    cursor = f" Próximo cursor: {result.next_after_id}." if result.next_after_id else ""
    return AdminOperationResult(
        True,
        f"{result.proposed} reparaciones de evidencia {verb}; quedan {result.remaining}.{cursor}",
    )


def _batch_vm(batch):
    return AdminOperationsReadinessBatchVM(
        batch_ref=str(batch.batch_ref),
        status=batch.status,
        environment=batch.environment,
        counts_label=f"{batch.valid_proposals} válidas · {batch.applied_proposals} aplicadas",
        reason=batch.reason,
        created_label=batch.created_at.strftime("%Y-%m-%d %H:%M"),
        detail_url=reverse("admin_operations_food_catalog_readiness_batch", args=[batch.batch_ref]),
    )


def _parse_food_ids(values):
    raw_values = values if isinstance(values, (list, tuple, set)) else str(values or "").split(",")
    try:
        return sorted({int(value) for value in raw_values if str(value).strip()})
    except (TypeError, ValueError) as exc:
        raise ValueError("Los IDs de alimentos deben ser números enteros.") from exc


def _trusted_source(food):
    return next((
        source for source in food.sources.all()
        if source.license_status == CatalogFoodSource.LICENSE_ALLOWED
        and source.source_name and source.source_food_id
    ), None)


def _source_label(source):
    return f"{source['name']} · {source['food_id']}" if source else "Sin fuente confiable"


def _value_label(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


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
                    f"dry-run #{batch.dry_run_batch_id}"
                    if batch.dry_run_batch_id
                    else ("plan" if batch.is_dry_run else "sin correlación")
                ),
                started_label=batch.started_at.strftime("%Y-%m-%d %H:%M"),
            )
            for batch in payload["batches"]
        ],
        enrichment_batches=build_catalog_enrichment_batch_vms(),
        source_options=list(payload["source_options"]),
        status_options=list(payload["status_options"]),
    )


__all__ = [
    "build_catalog_enrichment_batch_vms",
    "build_food_catalog_imports_vm",
    "build_food_catalog_readiness_vm",
    "build_readiness_batch_detail_vm",
    "perform_catalog_readiness_batch_operation",
    "perform_source_portion_backfill_operation",
    "prepare_catalog_readiness_operation",
]
