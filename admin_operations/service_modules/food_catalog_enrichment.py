"""Viewmodel projection for governed Food Catalog imports and enrichment."""

from admin_operations.selector_modules.food_catalog import get_food_catalog_import_batches_payload
from admin_operations.service_modules.common import _actor_label, _format_int
from admin_operations.viewmodels import (
    AdminOperationsCatalogEnrichmentBatchVM,
    AdminOperationsCatalogImportBatchVM,
    AdminOperationsCatalogImportsVM,
    AdminOperationsMetricVM,
)
from food_catalog.models import CatalogEnrichmentBatch, CatalogFood


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


__all__ = ["build_catalog_enrichment_batch_vms", "build_food_catalog_imports_vm"]
