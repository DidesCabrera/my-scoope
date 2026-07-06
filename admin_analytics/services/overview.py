from __future__ import annotations

from decimal import Decimal

from admin_analytics.filters import AdminAnalyticsFilters
from admin_analytics.selectors.overview import get_overview_metrics
from admin_analytics.viewmodels import (
    AdminAnalyticsHealthSignalVM,
    AdminAnalyticsKpiVM,
    AdminAnalyticsModuleVM,
    AdminAnalyticsOverviewVM,
    AdminAnalyticsSectionVM,
)


def _format_int(value) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def _format_usd(value) -> str:
    amount = Decimal(value or 0)
    return f"US$ {amount:.4f}"


def _status_for_ai(error_count: int, blocked_count: int) -> tuple[str, str]:
    if error_count > 0:
        return "warning", "Revisar errores IA"
    if blocked_count > 0:
        return "watch", "Bloqueos presentes"
    return "healthy", "Sin errores recientes"


def build_overview_vm(analytics_filters: AdminAnalyticsFilters | None = None) -> AdminAnalyticsOverviewVM:
    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    metrics = get_overview_metrics(analytics_filters=analytics_filters)
    product = metrics["product_activity"]
    ai = metrics["ai"]
    accounts = metrics["accounts"]
    proposals = metrics["proposals"]
    users = metrics["users"]

    north_star = product["weekly_active_nutrition_builders"]
    ai_status, ai_label = _status_for_ai(ai["error_7d"], ai["blocked_7d"])

    sections = [
        AdminAnalyticsSectionVM(
            title="Usuarios y activación",
            description="Base de usuarios, onboarding y usuarios construyendo valor nutricional.",
            kpis=[
                AdminAnalyticsKpiVM("Usuarios totales", _format_int(users["total"]), "Base registrada"),
                AdminAnalyticsKpiVM("Nuevos 7d", _format_int(users["new_7d"]), "Altas recientes"),
                AdminAnalyticsKpiVM("Nuevos 30d", _format_int(users["new_30d"]), "Crecimiento mensual"),
                AdminAnalyticsKpiVM(
                    "Onboarding completo",
                    _format_int(users["onboarding_completed"]),
                    "Profiles con ciclo nutricional listo",
                ),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Actividad nutricional",
            description="Creación de objetos centrales de My Scoope durante el período inicial.",
            kpis=[
                AdminAnalyticsKpiVM("Meals 7d", _format_int(product["meals_7d"]), f"Total: {_format_int(product['meals_total'])}"),
                AdminAnalyticsKpiVM(
                    "DailyPlans 7d",
                    _format_int(product["dailyplans_7d"]),
                    f"Total: {_format_int(product['dailyplans_total'])}",
                ),
                AdminAnalyticsKpiVM(
                    "Programs 7d",
                    _format_int(product["programs_7d"]),
                    f"Total: {_format_int(product['programs_total'])}",
                ),
                AdminAnalyticsKpiVM(
                    "Shares 7d",
                    _format_int(product["shares_7d"]),
                    "Intercambio nutricional",
                ),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="AI Assistant",
            description="Señales operacionales y económicas básicas del asistente IA.",
            kpis=[
                AdminAnalyticsKpiVM("Turnos IA 7d", _format_int(ai["turns_7d"]), f"Total: {_format_int(ai['turns_total'])}"),
                AdminAnalyticsKpiVM("Completados", _format_int(ai["completed_7d"]), "Status completed"),
                AdminAnalyticsKpiVM("Errores/bloqueos", f"{_format_int(ai['error_7d'])}/{_format_int(ai['blocked_7d'])}", "Error / blocked"),
                AdminAnalyticsKpiVM("Costo IA 7d", _format_usd(ai["estimated_cost_usd_7d"]), f"Tokens: {_format_int(ai['total_tokens_7d'])}"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Créditos y cuentas",
            description="Lectura inicial de wallets, suscripciones activas y movimientos de créditos.",
            kpis=[
                AdminAnalyticsKpiVM("Suscripciones activas", _format_int(accounts["active_subscriptions"]), "Trialing + active"),
                AdminAnalyticsKpiVM("Wallets", _format_int(accounts["wallets_total"]), "Cuentas con billetera"),
                AdminAnalyticsKpiVM("Créditos disponibles", _format_int(accounts["wallet_balance_total"]), f"Reservados: {_format_int(accounts['wallet_reserved_total'])}"),
                AdminAnalyticsKpiVM("Consumidos 7d", _format_int(accounts["credits_consumed_7d"]), f"Reservas: {_format_int(accounts['credits_reserved_7d'])}"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Propuestas IA",
            description="Volumen y aplicación de propuestas revisables creadas por IA.",
            kpis=[
                AdminAnalyticsKpiVM("Propuestas IA", _format_int(proposals["ai_proposals_total"]), "Total histórico"),
                AdminAnalyticsKpiVM("Creadas 7d", _format_int(proposals["ai_proposals_7d"]), "Source AI"),
                AdminAnalyticsKpiVM("Aplicadas 7d", _format_int(proposals["applied_7d"]), "Status applied"),
                AdminAnalyticsKpiVM("Comparaciones guardadas", _format_int(product["saved_comparisons_total"]), "Total histórico"),
            ],
        ),
    ]

    modules = [
        AdminAnalyticsModuleVM(
            title="Accounts",
            description="Planes, suscripciones, wallets y ledger comercial.",
            icon="credit-card",
            status="ADM03 implementado",
        ),
        AdminAnalyticsModuleVM(
            title="AI Assistant",
            description="Uso del LLM, tokens, costos, outcomes y bloqueos.",
            icon="bot",
            status="ADM04 implementado",
        ),
        AdminAnalyticsModuleVM(
            title="Product Activity",
            description="Actividad nutricional real en notas: Meals, DailyPlans, Programs, shares y comparaciones.",
            icon="activity",
            status="ADM05 implementado",
        ),
        AdminAnalyticsModuleVM(
            title="Food Catalog",
            description="Calidad, evidencia, imports, fuentes externas y cola de curaduría.",
            icon="database",
            status="ADM06 implementado",
        ),
        AdminAnalyticsModuleVM(
            title="Nutrition Solver",
            description="Calidad de propuestas, validaciones, desviaciones y readiness de alimentos.",
            icon="calculator",
            status="ADM07 implementado",
        ),
        AdminAnalyticsModuleVM(
            title="Alerts",
            description="Señales internas de riesgo para activar revisión operacional.",
            icon="badge-alert",
            status="ADM09 implementado",
        ),
    ]

    health_signals = [
        AdminAnalyticsHealthSignalVM(
            label="Activación nutricional",
            status="healthy" if north_star > 0 else "watch",
            value=_format_int(north_star),
            description="Weekly Active Nutrition Builders.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Costo IA",
            status="healthy",
            value=_format_usd(ai["estimated_cost_usd_7d"]),
            description="Costo estimado de usage events en 7 días.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Assistant",
            status=ai_status,
            value=ai_label,
            description="Errores y bloqueos recientes.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Créditos",
            status="watch" if accounts["wallet_reserved_total"] else "healthy",
            value=f"{_format_int(accounts['wallet_reserved_total'])} reservados",
            description="Reservas comerciales aún visibles en wallets.",
        ),
    ]

    return AdminAnalyticsOverviewVM(
        title="Admin Analytics",
        subtitle="Overview ejecutivo interno para observar activación, economía, IA y salud operacional de My Scoope.",
        north_star_metric="Weekly Active Nutrition Builders",
        north_star_description="Usuarios con actividad nutricional significativa en los últimos 7 días.",
        north_star_value=_format_int(north_star),
        generated_at=metrics["generated_at"],
        period_label=metrics["period_label"],
        filters=analytics_filters.as_template_context(),
        sections=sections,
        health_signals=health_signals,
        modules=modules,
    )
