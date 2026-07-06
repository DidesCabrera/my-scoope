from __future__ import annotations

from decimal import Decimal

from admin_analytics.filters import AdminAnalyticsFilters
from admin_analytics.selectors.food_catalog import get_food_catalog_metrics
from admin_analytics.viewmodels import (
    AdminAnalyticsFoodCatalogCandidateReasonRowVM,
    AdminAnalyticsFoodCatalogCandidateStatusRowVM,
    AdminAnalyticsFoodCatalogEvidenceRowVM,
    AdminAnalyticsFoodCatalogImportSourceRowVM,
    AdminAnalyticsFoodCatalogImportStatusRowVM,
    AdminAnalyticsFoodCatalogLicenseRowVM,
    AdminAnalyticsFoodCatalogProviderFetchRowVM,
    AdminAnalyticsFoodCatalogProviderReferenceRowVM,
    AdminAnalyticsFoodCatalogSourceRowVM,
    AdminAnalyticsFoodCatalogStatusRowVM,
    AdminAnalyticsFoodCatalogVM,
    AdminAnalyticsHealthSignalVM,
    AdminAnalyticsKpiVM,
    AdminAnalyticsSectionVM,
)


def _format_int(value) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def _format_decimal(value, digits: int = 1) -> str:
    amount = Decimal(str(value or 0))
    return f"{amount:.{digits}f}".replace(".", ",")


def _format_percent(numerator, denominator, digits: int = 0) -> str:
    denominator = Decimal(str(denominator or 0))
    if denominator <= 0:
        return "0%"
    ratio = Decimal(str(numerator or 0)) / denominator * Decimal("100")
    return f"{ratio:.{digits}f}%".replace(".", ",")


def _format_moneyless_quality(value) -> str:
    return f"{_format_decimal(value, 1)}/100"


def _format_label(value, fallback: str = "Sin dato") -> str:
    text = str(value or "").strip()
    return text or fallback


def build_food_catalog_vm(analytics_filters: AdminAnalyticsFilters | None = None) -> AdminAnalyticsFoodCatalogVM:
    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    metrics = get_food_catalog_metrics(analytics_filters=analytics_filters)
    catalog = metrics["catalog"]
    evidence = metrics["evidence"]
    imports = metrics["imports"]
    external = metrics["external"]
    curation = metrics["curation"]

    sections = [
        AdminAnalyticsSectionVM(
            title="Inventario maestro",
            description="Volumen y estado del catálogo maestro, separado de los alimentos operativos de notas.",
            kpis=[
                AdminAnalyticsKpiVM("CatalogFoods", _format_int(catalog["foods_total"]), f"7d/30d: {_format_int(catalog['foods_7d'])}/{_format_int(catalog['foods_30d'])}"),
                AdminAnalyticsKpiVM("Publicados/verificados", _format_int(catalog["published_or_verified"]), f"Publicado: {_format_int(catalog['published'])} · Verificado: {_format_int(catalog['verified'])}"),
                AdminAnalyticsKpiVM("Review queue", _format_int(catalog["review_queue"]), "Candidatos y alimentos pendientes de curaduría"),
                AdminAnalyticsKpiVM("Solver enabled", _format_int(catalog["solver_enabled"]), "Elegibles para futuras propuestas solver-ready"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Calidad y completitud",
            description="Señales de calidad nutricional, evidencia y campos que requieren revisión.",
            kpis=[
                AdminAnalyticsKpiVM("Quality avg", _format_moneyless_quality(catalog["avg_quality_score"]), "Promedio data_quality_score"),
                AdminAnalyticsKpiVM("Low quality", _format_int(catalog["low_quality"]), "data_quality_score < 60"),
                AdminAnalyticsKpiVM("Sin evidencia", _format_int(evidence["foods_without_sources"]), "CatalogFoods sin sources"),
                AdminAnalyticsKpiVM("Needs evidence", _format_int(catalog["needs_more_evidence"]), "Estado needs_more_evidence"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Imports y proveedores",
            description="Lectura operacional de batches, referencias externas y fetch logs recientes.",
            kpis=[
                AdminAnalyticsKpiVM("Batches 7d", _format_int(imports["batches_7d"]), f"Total: {_format_int(imports['batches_total'])}"),
                AdminAnalyticsKpiVM("Rows importadas", _format_int(imports["imported_rows"]), f"Fallidas: {_format_int(imports['failed_rows'])}"),
                AdminAnalyticsKpiVM("External refs", _format_int(external["references_total"]), f"Activas: {_format_int(external['active_references'])}"),
                AdminAnalyticsKpiVM("Fetch failed 7d", _format_int(external["fetch_failed_7d"]), f"Success: {_format_int(external['fetch_success_7d'])}"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Curaduría",
            description="Cola de candidatos y prioridad promedio para trabajo humano de Food Catalog.",
            kpis=[
                AdminAnalyticsKpiVM("Candidates", _format_int(curation["candidates_total"]), f"7d: {_format_int(curation['candidates_7d'])}"),
                AdminAnalyticsKpiVM("Queued", _format_int(curation["queued"]), "Pendientes de iniciar"),
                AdminAnalyticsKpiVM("In review", _format_int(curation["in_review"]), "En revisión"),
                AdminAnalyticsKpiVM("Priority avg", _format_decimal(curation["avg_priority"], 1), "0 bajo · 100 urgente"),
            ],
        ),
    ]

    total_foods = catalog["foods_total"]
    fetch_total = external["fetch_logs_7d"]
    quality_score = Decimal(str(catalog["avg_quality_score"] or 0))
    published_ratio = Decimal(str(catalog["published_or_verified"] or 0)) / Decimal(total_foods or 1)
    missing_evidence_ratio = Decimal(str(evidence["foods_without_sources"] or 0)) / Decimal(total_foods or 1)
    fetch_fail_ratio = Decimal(str(external["fetch_failed_7d"] or 0)) / Decimal(fetch_total or 1)

    health_signals = [
        AdminAnalyticsHealthSignalVM(
            label="Calidad promedio",
            status="healthy" if quality_score >= Decimal("70") else "watch",
            value=_format_moneyless_quality(catalog["avg_quality_score"]),
            description="Promedio de data_quality_score del catálogo maestro.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Publicación",
            status="healthy" if published_ratio >= Decimal("0.25") or total_foods == 0 else "watch",
            value=_format_percent(catalog["published_or_verified"], total_foods),
            description="Proporción publicada o verificada sobre CatalogFoods totales.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Evidencia",
            status="watch" if missing_evidence_ratio > Decimal("0.25") else "healthy",
            value=_format_int(evidence["foods_without_sources"]),
            description="CatalogFoods sin fuentes trazables registradas.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Fetch providers",
            status="watch" if fetch_fail_ratio > Decimal("0.20") else "healthy",
            value=_format_percent(external["fetch_failed_7d"], fetch_total),
            description="Tasa de fallos en fetch logs externos de los últimos 7 días.",
        ),
    ]

    status_rows = [
        AdminAnalyticsFoodCatalogStatusRowVM(
            status=_format_label(row["status"]),
            total=_format_int(row["total"]),
            created_7d=_format_int(row["created_7d"]),
            avg_quality=_format_moneyless_quality(row["avg_quality"]),
            solver_enabled=_format_int(row["solver_enabled"]),
        )
        for row in catalog["status_rows"]
    ]
    source_rows = [
        AdminAnalyticsFoodCatalogSourceRowVM(
            source_type=_format_label(row["source_type"]),
            total=_format_int(row["total"]),
            created_7d=_format_int(row["created_7d"]),
            avg_quality=_format_moneyless_quality(row["avg_quality"]),
            published=_format_int(row["published"]),
        )
        for row in catalog["source_rows"]
    ]
    evidence_rows = [
        AdminAnalyticsFoodCatalogEvidenceRowVM(
            label=row["label"],
            total=_format_int(row["total"]),
            foods_missing=_format_int(row["foods_missing"]),
            created_7d=_format_int(row["created_7d"]),
        )
        for row in evidence["rows"]
    ]
    license_rows = [
        AdminAnalyticsFoodCatalogLicenseRowVM(
            license_status=_format_label(row["license_status"]),
            total=_format_int(row["total"]),
            foods=_format_int(row["foods"]),
        )
        for row in evidence["license_rows"]
    ]
    import_status_rows = [
        AdminAnalyticsFoodCatalogImportStatusRowVM(
            status=_format_label(row["status"]),
            total=_format_int(row["total"]),
            rows=_format_int(row["rows"]),
            imported=_format_int(row["imported"]),
            skipped=_format_int(row["skipped"]),
            failed=_format_int(row["failed"]),
        )
        for row in imports["status_rows"]
    ]
    import_source_rows = [
        AdminAnalyticsFoodCatalogImportSourceRowVM(
            source_type=_format_label(row["source_type"]),
            total=_format_int(row["total"]),
            completed=_format_int(row["completed"]),
            failed=_format_int(row["failed"]),
            imported=_format_int(row["imported"]),
            failed_rows=_format_int(row["failed_rows"]),
        )
        for row in imports["source_rows"]
    ]
    provider_reference_rows = [
        AdminAnalyticsFoodCatalogProviderReferenceRowVM(
            provider=_format_label(row["provider"]),
            references=_format_int(row["references"]),
            active=_format_int(row["active"]),
            selected=_format_int(row["selected"]),
            seen=_format_int(row["seen"]),
            expired=_format_int(row["expired"]),
        )
        for row in external["provider_reference_rows"]
    ]
    provider_fetch_rows = [
        AdminAnalyticsFoodCatalogProviderFetchRowVM(
            provider=_format_label(row["provider"]),
            lookup_type=_format_label(row["lookup_type"]),
            total=_format_int(row["total"]),
            success=_format_int(row["success"]),
            failed=_format_int(row["failed"]),
            success_rate=_format_percent(row["success"], row["total"]),
        )
        for row in external["provider_fetch_rows"]
    ]
    candidate_status_rows = [
        AdminAnalyticsFoodCatalogCandidateStatusRowVM(
            status=_format_label(row["status"]),
            total=_format_int(row["total"]),
            avg_priority=_format_decimal(row["avg_priority"], 1),
            created_7d=_format_int(row["created_7d"]),
        )
        for row in curation["status_rows"]
    ]
    candidate_reason_rows = [
        AdminAnalyticsFoodCatalogCandidateReasonRowVM(
            reason=_format_label(row["reason"]),
            total=_format_int(row["total"]),
            avg_priority=_format_decimal(row["avg_priority"], 1),
        )
        for row in curation["reason_rows"]
    ]

    return AdminAnalyticsFoodCatalogVM(
        title="Food Catalog Analytics",
        subtitle="Calidad, curaduría, evidencia, imports y proveedores del catálogo maestro.",
        generated_at=metrics["generated_at"],
        period_label=metrics["period_label"],
        filters=analytics_filters.as_template_context(),
        sections=sections,
        health_signals=health_signals,
        status_rows=status_rows,
        source_rows=source_rows,
        evidence_rows=evidence_rows,
        license_rows=license_rows,
        import_status_rows=import_status_rows,
        import_source_rows=import_source_rows,
        provider_reference_rows=provider_reference_rows,
        provider_fetch_rows=provider_fetch_rows,
        candidate_status_rows=candidate_status_rows,
        candidate_reason_rows=candidate_reason_rows,
    )
