from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from admin_analytics.filters import AdminAnalyticsFilters
from admin_analytics.selectors.alerts import get_alert_metrics
from admin_analytics.viewmodels import (
    AdminAnalyticsAlertGroupVM,
    AdminAnalyticsAlertVM,
    AdminAnalyticsAlertsVM,
    AdminAnalyticsHealthSignalVM,
    AdminAnalyticsKpiVM,
    AdminAnalyticsSectionVM,
)

SEVERITY_ORDER = {"critical": 0, "warning": 1, "watch": 2, "info": 3}


@dataclass(frozen=True)
class _AlertCandidate:
    severity: str
    domain: str
    title: str
    value: str
    description: str
    recommendation: str


def _format_int(value) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def _format_usd(value) -> str:
    amount = Decimal(value or 0)
    return f"US$ {amount:.4f}"


def _format_percent(value, digits: int = 0) -> str:
    amount = Decimal(str(value or 0)) * Decimal("100")
    return f"{amount:.{digits}f}%".replace(".", ",")


def _ratio(numerator, denominator) -> Decimal:
    denominator = Decimal(str(denominator or 0))
    if denominator <= 0:
        return Decimal("0")
    return Decimal(str(numerator or 0)) / denominator


def _severity_label(severity: str) -> str:
    return {
        "critical": "Críticas",
        "warning": "Warnings",
        "watch": "Watch",
        "info": "Info",
    }.get(severity, severity.title())


def _to_vm(alert: _AlertCandidate) -> AdminAnalyticsAlertVM:
    return AdminAnalyticsAlertVM(
        severity=alert.severity,
        domain=alert.domain,
        title=alert.title,
        value=alert.value,
        description=alert.description,
        recommendation=alert.recommendation,
    )


def build_alerts_vm(analytics_filters: AdminAnalyticsFilters | None = None) -> AdminAnalyticsAlertsVM:
    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    metrics = get_alert_metrics(analytics_filters=analytics_filters)

    candidates = []
    candidates.extend(_product_alerts(metrics["product"]))
    candidates.extend(_ai_alerts(metrics["ai"]))
    candidates.extend(_account_alerts(metrics["accounts"]))
    candidates.extend(_food_catalog_alerts(metrics["food_catalog"]))
    candidates.extend(_solver_alerts(metrics["solver"]))

    candidates.sort(key=lambda alert: (SEVERITY_ORDER.get(alert.severity, 99), alert.domain, alert.title))
    alerts = [_to_vm(alert) for alert in candidates]

    counts = {severity: sum(1 for alert in candidates if alert.severity == severity) for severity in SEVERITY_ORDER}
    high_priority = counts["critical"] + counts["warning"]

    sections = [
        AdminAnalyticsSectionVM(
            title="Resumen de alertas",
            description="Conteo operativo de señales derivadas desde las métricas ya existentes.",
            kpis=[
                AdminAnalyticsKpiVM("Críticas", _format_int(counts["critical"]), "Requieren revisión prioritaria"),
                AdminAnalyticsKpiVM("Warnings", _format_int(counts["warning"]), "Riesgo operacional o económico"),
                AdminAnalyticsKpiVM("Watch", _format_int(counts["watch"]), "Observar evolución"),
                AdminAnalyticsKpiVM("Total", _format_int(len(alerts)), "Alertas visibles"),
            ],
        )
    ]

    health_signals = [
        AdminAnalyticsHealthSignalVM(
            label="Prioridad",
            status="warning" if high_priority else "healthy",
            value=_format_int(high_priority),
            description="Alertas críticas + warnings activas para el período seleccionado.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Producto",
            status="warning" if any(alert.domain == "Product Activity" and alert.severity in {"critical", "warning"} for alert in candidates) else "healthy",
            value=_format_int(sum(1 for alert in candidates if alert.domain == "Product Activity")),
            description="Señales de activación y actividad nutricional.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="IA y créditos",
            status="warning" if any(alert.domain in {"AI Assistant", "Accounts"} and alert.severity in {"critical", "warning"} for alert in candidates) else "healthy",
            value=_format_int(sum(1 for alert in candidates if alert.domain in {"AI Assistant", "Accounts"})),
            description="Costos, errores, bloqueos, reservas y wallets.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Calidad nutricional",
            status="warning" if any(alert.domain in {"Food Catalog", "Nutrition Solver"} and alert.severity in {"critical", "warning"} for alert in candidates) else "healthy",
            value=_format_int(sum(1 for alert in candidates if alert.domain in {"Food Catalog", "Nutrition Solver"})),
            description="Calidad de datos alimentarios y readiness del solver.",
        ),
    ]

    alert_groups = []
    for severity in SEVERITY_ORDER:
        grouped_alerts = [alert for alert in alerts if alert.severity == severity]
        if grouped_alerts:
            alert_groups.append(
                AdminAnalyticsAlertGroupVM(
                    title=_severity_label(severity),
                    description=_group_description(severity),
                    alerts=grouped_alerts,
                )
            )

    return AdminAnalyticsAlertsVM(
        title="Admin Analytics Alerts",
        subtitle="Centro interno de alertas read-only para detectar riesgo operacional, económico y de calidad en My Scoope.",
        generated_at=metrics["generated_at"],
        period_label=metrics["period_label"],
        filters=analytics_filters.as_template_context(),
        sections=sections,
        health_signals=health_signals,
        alert_groups=alert_groups,
        alerts=alerts,
    )


def _group_description(severity: str) -> str:
    if severity == "critical":
        return "Riesgos que podrían afectar operación, costos o calidad central del producto."
    if severity == "warning":
        return "Señales relevantes que conviene revisar antes de que escalen."
    if severity == "watch":
        return "Indicadores que no bloquean operación, pero deben observarse."
    return "Contexto útil para interpretar el estado del producto."


def _product_alerts(product: dict) -> list[_AlertCandidate]:
    north_star = product["north_star"]["weekly_active_nutrition_builders"]
    entities = product["entities"]
    shares = product["shares"]
    comparisons = product["comparisons"]
    alerts = []

    if north_star == 0:
        alerts.append(_AlertCandidate(
            "warning",
            "Product Activity",
            "Sin builders activos",
            "0",
            "No hay usuarios con actividad nutricional significativa en el período seleccionado.",
            "Revisar onboarding, flujo AI Assistant y creación de DailyPlans/Meals para detectar fricción de activación.",
        ))
    elif north_star < 3:
        alerts.append(_AlertCandidate(
            "watch",
            "Product Activity",
            "Activación baja",
            _format_int(north_star),
            "Hay pocos Weekly Active Nutrition Builders para el período seleccionado.",
            "Observar si la activación aumenta después de mejoras en assistant, onboarding o templates nutricionales.",
        ))

    if entities["dailyplans"]["created_7d"] == 0 and entities["meals"]["created_7d"] > 0:
        alerts.append(_AlertCandidate(
            "watch",
            "Product Activity",
            "Meals sin DailyPlans",
            f"{_format_int(entities['meals']['created_7d'])}/0",
            "Hay creación de Meals, pero no de DailyPlans durante el período.",
            "Revisar si el usuario logra convertir Meals en planes diarios o si falta guía desde el assistant.",
        ))

    if shares["sent_7d"] == 0 and shares["total"] > 0:
        alerts.append(_AlertCandidate(
            "info",
            "Product Activity",
            "Shares sin actividad reciente",
            "0",
            "Existen shares históricos, pero no hubo envíos en el período seleccionado.",
            "Considerar si compartir planes/meals debe aparecer como acción más visible en flujos de valor.",
        ))

    if comparisons["total"] > 0 and comparisons["updated_7d"] == 0:
        alerts.append(_AlertCandidate(
            "info",
            "Product Activity",
            "Comparaciones sin edición reciente",
            "0",
            "Hay comparaciones guardadas históricas, pero no fueron actualizadas en el período.",
            "Observar si el comparador está cumpliendo un rol de decisión o quedó como herramienta secundaria.",
        ))

    return alerts


def _ai_alerts(ai: dict) -> list[_AlertCandidate]:
    usage = ai["usage"]
    credits = ai["credits"]
    outcomes = ai["outcomes"]
    alerts = []

    event_count = usage["events_7d"]
    error_rate = _ratio(usage["error_7d"], event_count)
    blocked_rate = _ratio(usage["blocked_7d"], event_count)
    applied_rate = _ratio(outcomes["applied_7d"], outcomes["ai_proposals_7d"])

    if event_count > 0 and error_rate >= Decimal("0.20"):
        alerts.append(_AlertCandidate(
            "critical",
            "AI Assistant",
            "Error rate IA alto",
            _format_percent(error_rate),
            "Al menos 20% de los AIUsageEvent del período terminaron en error.",
            "Revisar provider logs, action_type con más error y fallback del ChatEngine antes de ampliar tráfico.",
        ))
    elif usage["error_7d"] > 0:
        alerts.append(_AlertCandidate(
            "warning",
            "AI Assistant",
            "Errores IA presentes",
            _format_int(usage["error_7d"]),
            "Hay usage events con status error durante el período.",
            "Usar la pantalla AI Assistant para identificar action_type, provider/model y usuarios afectados.",
        ))

    if event_count > 0 and blocked_rate >= Decimal("0.30"):
        alerts.append(_AlertCandidate(
            "warning",
            "AI Assistant",
            "Bloqueos IA elevados",
            _format_percent(blocked_rate),
            "Una proporción alta de turnos terminó bloqueada por guardrails, créditos o validaciones.",
            "Distinguir bloqueos esperados de seguridad versus bloqueos por configuración de créditos o tools.",
        ))

    if usage["estimated_cost_usd_7d"] > Decimal("1.00") and usage["completed_7d"] == 0:
        alerts.append(_AlertCandidate(
            "critical",
            "AI Assistant",
            "Costo IA sin completados",
            _format_usd(usage["estimated_cost_usd_7d"]),
            "Hay costo estimado en el período, pero ningún turno completado.",
            "Revisar cobro/registro de usage events y errores de proveedor antes de continuar pruebas intensivas.",
        ))
    elif usage["avg_cost_per_completed_turn_7d"] > Decimal("0.0500"):
        alerts.append(_AlertCandidate(
            "watch",
            "AI Assistant",
            "Costo por turno elevado",
            _format_usd(usage["avg_cost_per_completed_turn_7d"]),
            "El costo promedio por turno completado supera el umbral inicial de observación.",
            "Comparar modelos por action_type y considerar routing hacia modelos más baratos en tareas simples.",
        ))

    if credits["hard_blocked_quotas"] > 0:
        alerts.append(_AlertCandidate(
            "warning",
            "AI Assistant",
            "Usuarios bloqueados por cuota IA",
            _format_int(credits["hard_blocked_quotas"]),
            "Existen AIUserCreditQuota con hard_blocked=True en el período actual.",
            "Revisar si el bloqueo es correcto para el plan o si requiere ajustar límites comerciales.",
        ))

    if outcomes["ai_proposals_7d"] > 0 and applied_rate == 0:
        alerts.append(_AlertCandidate(
            "watch",
            "AI Assistant",
            "Propuestas IA sin aplicación",
            "0%",
            "Se crearon propuestas IA, pero ninguna fue aplicada en el período.",
            "Revisar calidad de propuestas, claridad de cards y flujo de aprobación antes de optimizar más generación.",
        ))

    return alerts


def _account_alerts(accounts: dict) -> list[_AlertCandidate]:
    wallets = accounts["wallets"]
    subscriptions = accounts["subscriptions"]
    ledger = accounts["ledger"]
    alerts = []

    reserved_ratio = _ratio(wallets["reserved_total"], wallets["balance_total"])
    if wallets["reserved_total"] > 0 and reserved_ratio >= Decimal("0.50"):
        alerts.append(_AlertCandidate(
            "warning",
            "Accounts",
            "Reservas de créditos altas",
            _format_percent(reserved_ratio),
            "Las reservas representan al menos la mitad del balance total de wallets.",
            "Revisar reservas no liberadas o flujos IA interrumpidos que puedan retener créditos.",
        ))
    elif wallets["with_reserved"] > 0:
        alerts.append(_AlertCandidate(
            "watch",
            "Accounts",
            "Wallets con créditos reservados",
            _format_int(wallets["with_reserved"]),
            "Hay wallets con reserved_balance mayor a cero.",
            "Verificar que las reservas correspondan a operaciones activas y no a estados colgados.",
        ))

    if subscriptions["past_due"] > 0:
        alerts.append(_AlertCandidate(
            "warning",
            "Accounts",
            "Suscripciones past_due",
            _format_int(subscriptions["past_due"]),
            "Existen suscripciones con estado past_due.",
            "Revisar cobranza, entitlements y comunicación al usuario antes de afectar acceso.",
        ))

    if ledger["credits_consumed_7d"] > 0 and ledger["entries_7d"] == 0:
        alerts.append(_AlertCandidate(
            "warning",
            "Accounts",
            "Consumo sin ledger visible",
            _format_int(ledger["credits_consumed_7d"]),
            "Hay consumo agregado, pero no entradas de ledger en el período.",
            "Revisar integridad de CreditLedger antes de usar estos datos para decisiones comerciales.",
        ))

    if subscriptions["active"] == 0 and accounts["plans"]["active"] > 0:
        alerts.append(_AlertCandidate(
            "info",
            "Accounts",
            "Planes activos sin suscripciones",
            "0",
            "Hay planes activos configurados, pero ninguna suscripción activa/trialing.",
            "Esperable en etapas tempranas; útil para monitorear cuando comience captación real.",
        ))

    return alerts


def _food_catalog_alerts(food_catalog: dict) -> list[_AlertCandidate]:
    catalog = food_catalog["catalog"]
    evidence = food_catalog["evidence"]
    external = food_catalog["external"]
    imports = food_catalog["imports"]
    total = catalog["foods_total"]
    alerts = []

    quality = Decimal(str(catalog["avg_quality_score"] or 0))
    if total > 0 and quality < Decimal("50"):
        alerts.append(_AlertCandidate(
            "warning",
            "Food Catalog",
            "Quality score bajo",
            f"{quality:.1f}/100".replace(".", ","),
            "El data_quality_score promedio del catálogo está bajo el umbral operativo inicial.",
            "Priorizar curaduría de alimentos usados por solver y revisar fuentes con baja calidad.",
        ))

    missing_sources_ratio = _ratio(evidence["foods_without_sources"], total)
    if total > 0 and missing_sources_ratio >= Decimal("0.50"):
        alerts.append(_AlertCandidate(
            "warning",
            "Food Catalog",
            "Muchos alimentos sin evidencia",
            _format_percent(missing_sources_ratio),
            "Al menos la mitad de los CatalogFood no tiene fuentes trazables registradas.",
            "Priorizar sources/licencias antes de usar el catálogo como base productiva amplia.",
        ))
    elif evidence["foods_without_sources"] > 0:
        alerts.append(_AlertCandidate(
            "watch",
            "Food Catalog",
            "Alimentos sin sources",
            _format_int(evidence["foods_without_sources"]),
            "Hay CatalogFoods sin evidencia trazable.",
            "Usar la pantalla Food Catalog para priorizar por status, source_type o calidad.",
        ))

    fetch_total = external["fetch_logs_7d"]
    fetch_fail_rate = _ratio(external["fetch_failed_7d"], fetch_total)
    if fetch_total > 0 and fetch_fail_rate >= Decimal("0.25"):
        alerts.append(_AlertCandidate(
            "warning",
            "Food Catalog",
            "Fallos altos en fetch externo",
            _format_percent(fetch_fail_rate),
            "La tasa de ExternalProviderFetchLog fallidos supera el umbral de observación.",
            "Revisar provider, lookup_type y límites de API antes de depender de importaciones automáticas.",
        ))

    if imports["running_or_pending"] > 0:
        alerts.append(_AlertCandidate(
            "watch",
            "Food Catalog",
            "Imports pendientes o corriendo",
            _format_int(imports["running_or_pending"]),
            "Hay batches en estado pending/running.",
            "Confirmar que no sean procesos colgados antes de ejecutar nuevas cargas.",
        ))

    return alerts


def _solver_alerts(solver: dict) -> list[_AlertCandidate]:
    proposals = solver["proposals"]
    quality = solver["solver_quality"]
    engine = solver["engine_validation"]
    readiness = solver["candidate_readiness"]
    alerts = []

    if proposals["total"] > 0 and proposals["with_solver_summary_total"] == 0 and proposals["with_engine_validation_total"] == 0:
        alerts.append(_AlertCandidate(
            "watch",
            "Nutrition Solver",
            "Propuestas sin trazabilidad solver",
            "0",
            "Existen propuestas, pero ninguna tiene nutrition_solver ni engine_validation en validation_summary.",
            "Mantener la observabilidad de validation_summary antes de evaluar calidad real del solver.",
        ))

    status_total = sum(int(row["total"] or 0) for row in quality["status_rows"])
    bad_total = sum(int(row["total"] or 0) for row in quality["status_rows"] if row["status"] in {"partial", "impossible"})
    bad_rate = _ratio(bad_total, status_total)
    if status_total > 0 and bad_rate >= Decimal("0.30"):
        alerts.append(_AlertCandidate(
            "warning",
            "Nutrition Solver",
            "Solver partial/impossible elevado",
            _format_percent(bad_rate),
            "Una proporción relevante de resultados solver termina partial o impossible.",
            "Revisar candidate readiness, restricciones y worst_macro antes de mejorar prompts o UI.",
        ))

    invalid_total = engine["invalid_total"]
    valid_total = engine["valid_total"]
    invalid_rate = _ratio(invalid_total, valid_total + invalid_total)
    if invalid_total > 0 and invalid_rate >= Decimal("0.20"):
        alerts.append(_AlertCandidate(
            "warning",
            "Nutrition Solver",
            "Validación estricta con errores",
            _format_percent(invalid_rate),
            "Al menos 20% de validaciones estrictas son inválidas.",
            "Revisar issue_rows y target_metric_rows para aislar la desviación dominante.",
        ))

    operational_total = readiness["operational_solver_enabled"]
    verified_ratio = _ratio(readiness["operational_verified_solver_enabled"], operational_total)
    if operational_total > 0 and verified_ratio < Decimal("0.50"):
        alerts.append(_AlertCandidate(
            "watch",
            "Nutrition Solver",
            "Pocos candidatos verificados",
            _format_percent(verified_ratio),
            "Menos de la mitad de los alimentos operacionales solver_enabled están verificados.",
            "Priorizar curaduría de alimentos base antes de exigir mayor precisión al solver.",
        ))

    if readiness["catalog_solver_candidates"] > 0 and readiness["catalog_solver_with_bounds"] == 0:
        alerts.append(_AlertCandidate(
            "watch",
            "Nutrition Solver",
            "Catalog candidates sin bounds",
            "0",
            "Hay CatalogFoods solver_enabled, pero ninguno tiene min/max portion bounds completos.",
            "Completar solver_min_portion_g y solver_max_portion_g para mejorar propuestas determinísticas.",
        ))

    return alerts
