from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db.models import Count, Q, QuerySet, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from ai_assistant.application.credits import current_period
from ai_assistant.models import AICreditLedger, AIUsageEvent, AIUserCreditQuota


@dataclass(frozen=True)
class AIUsageKpis:
    period: str
    total_events: int = 0
    completed_events: int = 0
    blocked_events: int = 0
    error_events: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    estimated_cost_usd: Decimal = Decimal("0")
    charged_credits: int = 0
    active_users: int = 0


@dataclass(frozen=True)
class AIUsageDashboardReport:
    period: str
    generated_at: Any
    kpis: AIUsageKpis
    by_action_type: list[dict[str, Any]]
    by_model: list[dict[str, Any]]
    by_credit_plan: list[dict[str, Any]]
    top_users: list[dict[str, Any]]
    recent_events: list[AIUsageEvent]
    quota_pressure: list[dict[str, Any]]


def build_ai_usage_dashboard_report(*, period: str | None = None, recent_limit: int = 25) -> AIUsageDashboardReport:
    """Build an internal AI usage/cost dashboard report.

    This report intentionally aggregates internal cost metrics for admins only.
    Tokens and estimated USD costs remain implementation details; user-facing
    pricing continues to use AI credits.
    """

    selected_period = period or current_period()
    events = AIUsageEvent.objects.filter(period=selected_period)
    kpis = _build_kpis(period=selected_period, events=events)
    return AIUsageDashboardReport(
        period=selected_period,
        generated_at=timezone.now(),
        kpis=kpis,
        by_action_type=_usage_breakdown(events, "action_type", limit=15),
        by_model=_usage_breakdown(events, "model_name", extra_group_fields=("provider",), limit=15),
        by_credit_plan=_usage_breakdown(events, "credit_plan_code", limit=10),
        top_users=_top_users(events, limit=15),
        recent_events=list(events.select_related("user")[:recent_limit]),
        quota_pressure=_quota_pressure(period=selected_period, limit=15),
    )


def _build_kpis(*, period: str, events: QuerySet[AIUsageEvent]) -> AIUsageKpis:
    aggregates = events.aggregate(
        total_events=Count("id"),
        total_tokens=Coalesce(Sum("total_tokens"), 0),
        input_tokens=Coalesce(Sum("input_tokens"), 0),
        output_tokens=Coalesce(Sum("output_tokens"), 0),
        cached_input_tokens=Coalesce(Sum("cached_input_tokens"), 0),
        estimated_cost_usd=Coalesce(Sum("estimated_cost_usd"), Decimal("0")),
        charged_credits=Coalesce(Sum("charged_credits"), 0),
        active_users=Count("user", distinct=True),
    )
    return AIUsageKpis(
        period=period,
        total_events=int(aggregates["total_events"] or 0),
        completed_events=events.filter(status=AIUsageEvent.Status.COMPLETED).count(),
        blocked_events=events.filter(status=AIUsageEvent.Status.BLOCKED).count(),
        error_events=events.filter(status=AIUsageEvent.Status.ERROR).count(),
        total_tokens=int(aggregates["total_tokens"] or 0),
        input_tokens=int(aggregates["input_tokens"] or 0),
        output_tokens=int(aggregates["output_tokens"] or 0),
        cached_input_tokens=int(aggregates["cached_input_tokens"] or 0),
        estimated_cost_usd=aggregates["estimated_cost_usd"] or Decimal("0"),
        charged_credits=int(aggregates["charged_credits"] or 0),
        active_users=int(aggregates["active_users"] or 0),
    )


def _usage_breakdown(
    events: QuerySet[AIUsageEvent],
    group_field: str,
    *,
    extra_group_fields: tuple[str, ...] = (),
    limit: int = 10,
) -> list[dict[str, Any]]:
    group_fields = (group_field, *extra_group_fields)
    rows = (
        events.values(*group_fields)
        .annotate(
            events_count=Count("id"),
            total_tokens=Coalesce(Sum("total_tokens"), 0),
            estimated_cost_usd=Coalesce(Sum("estimated_cost_usd"), Decimal("0")),
            charged_credits=Coalesce(Sum("charged_credits"), 0),
            blocked_events=Count("id", filter=Q(status=AIUsageEvent.Status.BLOCKED)),
            error_events=Count("id", filter=Q(status=AIUsageEvent.Status.ERROR)),
        )
        .order_by("-estimated_cost_usd", "-total_tokens", "-events_count")[:limit]
    )
    return [dict(row) for row in rows]


def _top_users(events: QuerySet[AIUsageEvent], *, limit: int = 10) -> list[dict[str, Any]]:
    rows = (
        events.filter(user__isnull=False)
        .values("user_id", "user__username", "user__email")
        .annotate(
            events_count=Count("id"),
            total_tokens=Coalesce(Sum("total_tokens"), 0),
            estimated_cost_usd=Coalesce(Sum("estimated_cost_usd"), Decimal("0")),
            charged_credits=Coalesce(Sum("charged_credits"), 0),
            blocked_events=Count("id", filter=Q(status=AIUsageEvent.Status.BLOCKED)),
            error_events=Count("id", filter=Q(status=AIUsageEvent.Status.ERROR)),
        )
        .order_by("-estimated_cost_usd", "-total_tokens", "-charged_credits")[:limit]
    )
    return [dict(row) for row in rows]


def _quota_pressure(*, period: str, limit: int = 10) -> list[dict[str, Any]]:
    quotas = AIUserCreditQuota.objects.filter(period=period, monthly_credit_limit__gt=0).select_related("user")
    rows: list[dict[str, Any]] = []
    for quota in quotas:
        usage_ratio = Decimal(quota.credits_used) / Decimal(quota.monthly_credit_limit)
        rows.append(
            {
                "user_id": quota.user_id,
                "username": getattr(quota.user, "username", ""),
                "email": getattr(quota.user, "email", ""),
                "plan_code": quota.plan_code,
                "credits_used": quota.credits_used,
                "monthly_credit_limit": quota.monthly_credit_limit,
                "daily_credit_limit": quota.daily_credit_limit,
                "usage_ratio": usage_ratio,
                "hard_blocked": quota.hard_blocked,
            }
        )
    rows.sort(key=lambda row: (row["hard_blocked"], row["usage_ratio"], row["credits_used"]), reverse=True)
    return rows[:limit]


def build_ai_credit_ledger_summary(*, period: str | None = None) -> dict[str, Any]:
    selected_period = period or current_period()
    aggregate = AICreditLedger.objects.filter(period=selected_period).aggregate(
        entries=Count("id"),
        charged_credits=Coalesce(Sum("credits"), 0),
    )
    return {
        "period": selected_period,
        "entries": int(aggregate["entries"] or 0),
        "charged_credits": int(aggregate["charged_credits"] or 0),
    }
