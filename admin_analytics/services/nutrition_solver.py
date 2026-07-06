from __future__ import annotations

from admin_analytics.filters import AdminAnalyticsFilters
from admin_analytics.selectors.nutrition_solver import get_nutrition_solver_metrics
from admin_analytics.viewmodels import (
    AdminAnalyticsHealthSignalVM,
    AdminAnalyticsKpiVM,
    AdminAnalyticsNutritionSolverVM,
    AdminAnalyticsSectionVM,
    AdminAnalyticsSolverCatalogStatusRowVM,
    AdminAnalyticsSolverConfigRowVM,
    AdminAnalyticsSolverIssueRowVM,
    AdminAnalyticsSolverOperationalGroupRowVM,
    AdminAnalyticsSolverReasonRowVM,
    AdminAnalyticsSolverSourceRowVM,
    AdminAnalyticsSolverStatusRowVM,
    AdminAnalyticsSolverTargetMetricRowVM,
    AdminAnalyticsSolverWorstMacroRowVM,
)


def _format_int(value) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def _format_decimal(value, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_percent(numerator, denominator) -> str:
    denominator = float(denominator or 0)
    if denominator <= 0:
        return "—"
    return f"{(float(numerator or 0) / denominator) * 100:.1f}%".replace(".", ",")


def _format_boolish(value) -> str:
    if value is True:
        return "Sí"
    if value is False:
        return "No"
    return "—"


def _format_label(value) -> str:
    value = str(value or "—")
    return value.replace("_", " ").title()


def build_nutrition_solver_vm(analytics_filters: AdminAnalyticsFilters | None = None) -> AdminAnalyticsNutritionSolverVM:
    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    metrics = get_nutrition_solver_metrics(analytics_filters=analytics_filters)
    proposals = metrics["proposals"]
    solver = metrics["solver_quality"]
    engine = metrics["engine_validation"]
    readiness = metrics["candidate_readiness"]

    sections = [
        AdminAnalyticsSectionVM(
            title="Cobertura de validación",
            description="Cuántas propuestas quedan con señales observables del solver o de validación estricta.",
            kpis=[
                AdminAnalyticsKpiVM("Proposals total", _format_int(proposals["total"]), "Base de propuestas históricas."),
                AdminAnalyticsKpiVM("Solver summaries", _format_int(proposals["with_solver_summary_total"]), "Propuestas con validation_summary.nutrition_solver."),
                AdminAnalyticsKpiVM("Solver 7d", _format_int(proposals["with_solver_summary_7d"]), "Propuestas generadas por solver en los últimos 7 días."),
                AdminAnalyticsKpiVM("Engine validation", _format_int(proposals["with_engine_validation_total"]), "Propuestas con validación estricta diaria."),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Calidad del resultado solver",
            description="Status, desviación macro, score e iteraciones reportadas por contratos del Nutrition Solver.",
            kpis=[
                AdminAnalyticsKpiVM("Avg score", _format_decimal(solver["avg_score"], 4), "Menor es mejor según scoring_config."),
                AdminAnalyticsKpiVM("Avg iterations", _format_decimal(solver["avg_iterations"], 1), "Promedio de iteraciones reportadas."),
                AdminAnalyticsKpiVM("Avg candidates", _format_decimal(solver["avg_candidate_count"], 1), "Candidatos disponibles por propuesta solver."),
                AdminAnalyticsKpiVM("Avg worst deviation", f"{_format_decimal(solver['avg_worst_deviation_percent'], 1)}%", "Peor desviación macro promedio."),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Validación estricta",
            description="Señales de validator: valid/invalid, warnings, errors e issues frecuentes.",
            kpis=[
                AdminAnalyticsKpiVM("Valid results", _format_int(engine["valid_total"]), "engine_validation.is_valid=True."),
                AdminAnalyticsKpiVM("Invalid results", _format_int(engine["invalid_total"]), "engine_validation.is_valid=False."),
                AdminAnalyticsKpiVM("Warnings", _format_int(engine["warnings_total"]), "Propuestas con warnings."),
                AdminAnalyticsKpiVM("Errors", _format_int(engine["errors_total"]), "Propuestas con errores."),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Candidate readiness",
            description="Disponibilidad de alimentos operacionales y catálogo maestro habilitados para solver.",
            kpis=[
                AdminAnalyticsKpiVM("Operational solver foods", _format_int(readiness["operational_solver_enabled"]), "notas.Food activos con solver_enabled."),
                AdminAnalyticsKpiVM("Verified operational", _format_int(readiness["operational_verified_solver_enabled"]), "Candidatos operacionales verificados."),
                AdminAnalyticsKpiVM("Catalog candidates", _format_int(readiness["catalog_solver_candidates"]), "CatalogFood publicados/verificados con solver_enabled."),
                AdminAnalyticsKpiVM("Catalog high quality", _format_int(readiness["catalog_solver_high_quality"]), "Catalog candidates con quality >= 80."),
            ],
        ),
    ]

    health_signals = [
        _coverage_signal(proposals),
        _solver_status_signal(solver),
        _engine_validation_signal(engine),
        _candidate_readiness_signal(readiness),
    ]

    solver_status_rows = [
        AdminAnalyticsSolverStatusRowVM(status=_format_label(row["status"]), total=_format_int(row["total"]))
        for row in solver["status_rows"]
    ]
    solver_reason_rows = [
        AdminAnalyticsSolverReasonRowVM(reason_code=row["reason_code"], total=_format_int(row["total"]))
        for row in solver["reason_rows"]
    ]
    solver_worst_macro_rows = [
        AdminAnalyticsSolverWorstMacroRowVM(macro=_format_label(row["macro"]), total=_format_int(row["total"]))
        for row in solver["worst_macro_rows"]
    ]
    solver_source_rows = [
        AdminAnalyticsSolverSourceRowVM(
            source=_format_label(row["source"]),
            total=_format_int(row["total"]),
            optimal=_format_int(row["optimal"]),
            acceptable=_format_int(row["acceptable"]),
            partial=_format_int(row["partial"]),
            impossible=_format_int(row["impossible"]),
            avg_score=_format_decimal(row["avg_score"], 4),
        )
        for row in solver["source_rows"]
    ]
    engine_status_rows = [
        AdminAnalyticsSolverStatusRowVM(status=_format_label(row["status"]), total=_format_int(row["total"]))
        for row in engine["status_rows"]
    ]
    issue_rows = [
        AdminAnalyticsSolverIssueRowVM(
            severity=_format_label(row["severity"]),
            code=row["code"],
            metric=_format_label(row["metric"]),
            total=_format_int(row["total"]),
        )
        for row in engine["issue_rows"]
    ]
    target_metric_rows = [
        AdminAnalyticsSolverTargetMetricRowVM(
            metric=_format_label(row["metric"]),
            samples=_format_int(row["samples"]),
            avg_abs_diff_percent=f"{_format_decimal(row['avg_abs_diff_percent'], 1)}%",
            max_abs_diff_percent=f"{_format_decimal(row['max_abs_diff_percent'], 1)}%",
        )
        for row in engine["metric_rows"]
    ]
    catalog_status_rows = [
        AdminAnalyticsSolverCatalogStatusRowVM(
            status=_format_label(row["status"]),
            total=_format_int(row["total"]),
            high_quality=_format_int(row["high_quality"]),
        )
        for row in readiness["catalog_status_rows"]
    ]
    operational_group_rows = [
        AdminAnalyticsSolverOperationalGroupRowVM(
            food_group=_format_label(row["food_group"] or "sin_grupo"),
            total=_format_int(row["total"]),
            verified=_format_int(row["verified"]),
        )
        for row in readiness["operational_group_rows"]
    ]
    config_rows = _build_config_rows(metrics["config"])

    return AdminAnalyticsNutritionSolverVM(
        title="Nutrition Solver Analytics",
        subtitle="Calidad de optimización, validación estricta y readiness de candidatos del motor nutricional.",
        generated_at=metrics["generated_at"],
        period_label=metrics["period_label"],
        filters=analytics_filters.as_template_context(),
        sections=sections,
        health_signals=health_signals,
        solver_status_rows=solver_status_rows,
        solver_reason_rows=solver_reason_rows,
        solver_worst_macro_rows=solver_worst_macro_rows,
        solver_source_rows=solver_source_rows,
        engine_status_rows=engine_status_rows,
        issue_rows=issue_rows,
        target_metric_rows=target_metric_rows,
        catalog_status_rows=catalog_status_rows,
        operational_group_rows=operational_group_rows,
        config_rows=config_rows,
    )


def _coverage_signal(proposals: dict) -> AdminAnalyticsHealthSignalVM:
    coverage = _format_percent(proposals["with_solver_summary_total"] + proposals["with_engine_validation_total"], proposals["total"])
    status = "ok" if proposals["total"] == 0 or coverage != "—" else "warning"
    return AdminAnalyticsHealthSignalVM(
        label="Cobertura",
        status=status,
        value=coverage,
        description="Propuestas con nutrition_solver o engine_validation en validation_summary.",
    )


def _solver_status_signal(solver: dict) -> AdminAnalyticsHealthSignalVM:
    total = sum(int(row["total"]) for row in solver["status_rows"])
    bad = sum(int(row["total"]) for row in solver["status_rows"] if row["status"] in {"partial", "impossible"})
    status = "ok" if total == 0 or bad == 0 else "warning"
    return AdminAnalyticsHealthSignalVM(
        label="Solver status",
        status=status,
        value=_format_percent(total - bad, total),
        description="Porcentaje de resultados optimal/acceptable entre summaries del solver.",
    )


def _engine_validation_signal(engine: dict) -> AdminAnalyticsHealthSignalVM:
    total = engine["valid_total"] + engine["invalid_total"]
    status = "ok" if engine["invalid_total"] == 0 else "warning"
    return AdminAnalyticsHealthSignalVM(
        label="Strict validation",
        status=status,
        value=_format_percent(engine["valid_total"], total),
        description="Propuestas válidas según engine_validation.is_valid.",
    )


def _candidate_readiness_signal(readiness: dict) -> AdminAnalyticsHealthSignalVM:
    total = readiness["operational_solver_enabled"]
    verified = readiness["operational_verified_solver_enabled"]
    status = "ok" if total == 0 or verified >= max(1, total // 2) else "warning"
    return AdminAnalyticsHealthSignalVM(
        label="Candidate readiness",
        status=status,
        value=_format_percent(verified, total),
        description="Candidatos operacionales solver_enabled que además están verificados.",
    )


def _build_config_rows(config: dict) -> list[AdminAnalyticsSolverConfigRowVM]:
    rows = []
    for key, value in config["portion_solver"].items():
        rows.append(AdminAnalyticsSolverConfigRowVM("Portion solver", key, str(value)))
    for key, value in config["optimization_scoring"].items():
        rows.append(AdminAnalyticsSolverConfigRowVM("Optimization scoring", key, str(value)))
    for key, value in config["warning_tolerance_percent"].items():
        rows.append(AdminAnalyticsSolverConfigRowVM("Warning tolerance", key, f"{value}%"))
    for key, value in config["error_tolerance_percent"].items():
        rows.append(AdminAnalyticsSolverConfigRowVM("Error tolerance", key, f"{value}%"))
    for key, value in config["reasonable_max_portion_g_by_role"].items():
        rows.append(AdminAnalyticsSolverConfigRowVM("Max portion by role", key, f"{value} g"))
    return rows
