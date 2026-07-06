from __future__ import annotations

from decimal import Decimal

from admin_analytics.filters import AdminAnalyticsFilters
from admin_analytics.selectors.ai_assistant import get_ai_assistant_metrics
from admin_analytics.viewmodels import (
    AdminAnalyticsAIAssistantActionRowVM,
    AdminAnalyticsAIAssistantCreditPlanRowVM,
    AdminAnalyticsAIAssistantModelRowVM,
    AdminAnalyticsAIAssistantQuotaRowVM,
    AdminAnalyticsAIAssistantUserRowVM,
    AdminAnalyticsAIAssistantVM,
    AdminAnalyticsHealthSignalVM,
    AdminAnalyticsKpiVM,
    AdminAnalyticsLedgerKindRowVM,
    AdminAnalyticsSectionVM,
)


def _format_int(value) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def _format_usd(value) -> str:
    amount = Decimal(value or 0)
    return f"US$ {amount:.4f}"


def _format_ms(value) -> str:
    if not value:
        return "—"
    return f"{int(value):,} ms".replace(",", ".")


def _format_percent(value) -> str:
    amount = Decimal(value or 0) * Decimal("100")
    return f"{amount:.0f}%"


def _format_label(value, fallback: str = "Sin dato") -> str:
    text = str(value or "").strip()
    return text or fallback


def _rate(numerator, denominator) -> Decimal:
    denominator = int(denominator or 0)
    if denominator <= 0:
        return Decimal("0")
    return Decimal(int(numerator or 0)) / Decimal(denominator)


def build_ai_assistant_vm(analytics_filters: AdminAnalyticsFilters | None = None) -> AdminAnalyticsAIAssistantVM:
    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    metrics = get_ai_assistant_metrics(analytics_filters=analytics_filters)
    usage = metrics["usage"]
    breakdowns = metrics["breakdowns"]
    credits = metrics["credits"]
    outcomes = metrics["outcomes"]

    error_rate = _rate(usage["error_7d"], usage["events_7d"])
    blocked_rate = _rate(usage["blocked_7d"], usage["events_7d"])
    applied_rate = _rate(outcomes["applied_7d"], outcomes["ai_proposals_7d"])

    sections = [
        AdminAnalyticsSectionVM(
            title="Uso y estado",
            description="Volumen de turnos, usuarios activos, status y latencia del asistente.",
            kpis=[
                AdminAnalyticsKpiVM("Turnos IA 7d", _format_int(usage["events_7d"]), f"Total: {_format_int(usage['events_total'])}"),
                AdminAnalyticsKpiVM("Usuarios activos IA", _format_int(usage["active_users_7d"]), "Usuarios con AIUsageEvent"),
                AdminAnalyticsKpiVM("Completed / error / blocked", f"{_format_int(usage['completed_7d'])}/{_format_int(usage['error_7d'])}/{_format_int(usage['blocked_7d'])}", "Status 7d"),
                AdminAnalyticsKpiVM("Latencia promedio", _format_ms(usage["avg_latency_ms_7d"]), "AIUsageEvent.latency_ms"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Tokens y costo",
            description="Costo interno estimado; los usuarios siguen viendo créditos, no tokens.",
            kpis=[
                AdminAnalyticsKpiVM("Tokens totales", _format_int(usage["total_tokens_7d"]), "Input + output"),
                AdminAnalyticsKpiVM("Input / output", f"{_format_int(usage['input_tokens_7d'])}/{_format_int(usage['output_tokens_7d'])}", f"Cached: {_format_int(usage['cached_input_tokens_7d'])}"),
                AdminAnalyticsKpiVM("Costo estimado", _format_usd(usage["estimated_cost_usd_7d"]), "Últimos 7 días"),
                AdminAnalyticsKpiVM("Costo por completed", _format_usd(usage["avg_cost_per_completed_turn_7d"]), "Promedio simple"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Tools y créditos IA",
            description="Uso agregado de tools, créditos cobrados y cuotas AI transicionales.",
            kpis=[
                AdminAnalyticsKpiVM("Tool calls", _format_int(usage["tool_calls_7d"]), f"Turnos con tools: {_format_int(usage['events_with_tools_7d'])}"),
                AdminAnalyticsKpiVM("Créditos cargados", _format_int(usage["charged_credits_7d"]), "AIUsageEvent.charged_credits"),
                AdminAnalyticsKpiVM("Ledger IA 7d", _format_int(credits["ledger_entries_7d"]), f"Créditos: {_format_int(credits['ledger_credits_7d'])}"),
                AdminAnalyticsKpiVM("Cuotas bloqueadas", _format_int(credits["hard_blocked_quotas"]), f"Cuotas periodo: {_format_int(credits['quotas_total'])}"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Outcomes nutricionales",
            description="Propuestas y chats creados por la experiencia IA.",
            kpis=[
                AdminAnalyticsKpiVM("Propuestas IA 7d", _format_int(outcomes["ai_proposals_7d"]), f"Total: {_format_int(outcomes['ai_proposals_total'])}"),
                AdminAnalyticsKpiVM("Aplicadas 7d", _format_int(outcomes["applied_7d"]), f"Tasa: {_format_percent(applied_rate)}"),
                AdminAnalyticsKpiVM("Pendientes / rechazadas", f"{_format_int(outcomes['pending_review_7d'])}/{_format_int(outcomes['rejected_7d'])}", "Últimos 7 días"),
                AdminAnalyticsKpiVM("Chats IA", _format_int(outcomes["chats_total"]), f"Activos: {_format_int(outcomes['active_chats'])}"),
            ],
        ),
    ]

    health_signals = [
        AdminAnalyticsHealthSignalVM(
            label="Errores IA",
            status="warning" if error_rate > Decimal("0.05") else "healthy",
            value=_format_percent(error_rate),
            description="Tasa de AIUsageEvent status=error en los últimos 7 días.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Bloqueos IA",
            status="watch" if usage["blocked_7d"] else "healthy",
            value=_format_int(usage["blocked_7d"]),
            description="Bloqueos por guardrails, créditos u otras protecciones registradas.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Costo IA",
            status="watch" if Decimal(usage["estimated_cost_usd_7d"] or 0) > Decimal("1") else "healthy",
            value=_format_usd(usage["estimated_cost_usd_7d"]),
            description="Costo estimado acumulado del período inicial.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Outcomes",
            status="healthy" if outcomes["applied_7d"] else "watch",
            value=_format_int(outcomes["applied_7d"]),
            description="Propuestas IA aplicadas en los últimos 7 días.",
        ),
    ]

    action_rows = [
        AdminAnalyticsAIAssistantActionRowVM(
            action_type=_format_label(row["action_type"]),
            events=_format_int(row["events"]),
            completed=_format_int(row["completed"]),
            errors=_format_int(row["errors"]),
            blocked=_format_int(row["blocked"]),
            total_tokens=_format_int(row["total_tokens"]),
            estimated_cost_usd=_format_usd(row["estimated_cost_usd"]),
            charged_credits=_format_int(row["charged_credits"]),
            tool_calls=_format_int(row["tool_calls"]),
        )
        for row in breakdowns["by_action_type_7d"]
    ]

    model_rows = [
        AdminAnalyticsAIAssistantModelRowVM(
            provider=_format_label(row["provider"]),
            model_name=_format_label(row["model_name"]),
            events=_format_int(row["events"]),
            total_tokens=_format_int(row["total_tokens"]),
            estimated_cost_usd=_format_usd(row["estimated_cost_usd"]),
            charged_credits=_format_int(row["charged_credits"]),
            avg_latency_ms=_format_ms(row["avg_latency_ms"]),
        )
        for row in breakdowns["by_provider_model_7d"]
    ]

    credit_plan_rows = [
        AdminAnalyticsAIAssistantCreditPlanRowVM(
            credit_plan_code=_format_label(row["credit_plan_code"], "Sin plan"),
            events=_format_int(row["events"]),
            active_users=_format_int(row["active_users"]),
            charged_credits=_format_int(row["charged_credits"]),
            estimated_cost_usd=_format_usd(row["estimated_cost_usd"]),
        )
        for row in breakdowns["by_credit_plan_7d"]
    ]

    user_rows = [
        AdminAnalyticsAIAssistantUserRowVM(
            email=_format_label(row["user__email"] or row["user__username"]),
            username=_format_label(row["user__username"]),
            events=_format_int(row["events"]),
            total_tokens=_format_int(row["total_tokens"]),
            estimated_cost_usd=_format_usd(row["estimated_cost_usd"]),
            charged_credits=_format_int(row["charged_credits"]),
            blocked=_format_int(row["blocked"]),
            errors=_format_int(row["errors"]),
        )
        for row in breakdowns["top_users_7d"]
    ]

    quota_rows = [
        AdminAnalyticsAIAssistantQuotaRowVM(
            email=row["email"],
            username=row["username"],
            plan_code=row["plan_code"],
            credits_used=_format_int(row["credits_used"]),
            monthly_credit_limit=_format_int(row["monthly_credit_limit"]),
            daily_credit_limit=_format_int(row["daily_credit_limit"]),
            usage_ratio=_format_percent(row["usage_ratio"]),
            hard_blocked="Sí" if row["hard_blocked"] else "No",
        )
        for row in credits["quota_rows"]
    ]

    ledger_kind_rows = [
        AdminAnalyticsLedgerKindRowVM(
            kind=row["kind"],
            entries=_format_int(row["entries"]),
            credits_delta=_format_int(row["credits"]),
            reserved_delta="—",
        )
        for row in credits["ledger_by_kind_7d"]
    ]

    return AdminAnalyticsAIAssistantVM(
        title="AI Assistant Analytics",
        subtitle="Métricas operacionales read-only para usage, tools, costos, créditos y outcomes del asistente.",
        generated_at=metrics["generated_at"],
        period_label=metrics["period_label"],
        filters=analytics_filters.as_template_context(),
        current_period=metrics["current_period"],
        sections=sections,
        health_signals=health_signals,
        action_rows=action_rows,
        model_rows=model_rows,
        credit_plan_rows=credit_plan_rows,
        user_rows=user_rows,
        quota_rows=quota_rows,
        ledger_kind_rows=ledger_kind_rows,
    )
