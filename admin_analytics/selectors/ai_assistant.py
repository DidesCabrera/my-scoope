from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from accounts.models import CreditLedger
from accounts.services.ai_credits import AI_CREDIT_REFERENCE_TYPE, list_account_ai_credit_quotas
from admin_analytics.filters import AdminAnalyticsFilters
from ai_assistant.application.credits import current_period
from ai_assistant.models import AIUsageEvent
from notas.domain.model_modules.proposals import AiNutritionChat, NutritionProposal


def _sum(queryset, field: str):
    return queryset.aggregate(total=Sum(field))["total"] or 0


def _avg(queryset, field: str):
    return queryset.aggregate(avg=Avg(field))["avg"] or 0


def get_ai_assistant_metrics(*, now=None, analytics_filters: AdminAnalyticsFilters | None = None, top_limit: int = 10) -> dict:
    """Return ADM04 read-only AI Assistant operations metrics.

    The selector only consumes existing operational data from `ai_assistant` and
    proposal/chat records from `notas`. It does not create analytical snapshots.
    """

    now = now or timezone.now()
    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    since_7d = analytics_filters.since(now=now)
    since_30d = now - timedelta(days=30)
    period = current_period()

    usage = analytics_filters.apply_user_segment(AIUsageEvent.objects.all(), "user")
    usage_7d = usage.filter(created_at__gte=since_7d)
    usage_30d = usage.filter(created_at__gte=since_30d)

    usage_aggregates_7d = usage_7d.aggregate(
        total_tokens=Sum("total_tokens"),
        input_tokens=Sum("input_tokens"),
        cached_input_tokens=Sum("cached_input_tokens"),
        output_tokens=Sum("output_tokens"),
        estimated_cost_usd=Sum("estimated_cost_usd"),
        charged_credits=Sum("charged_credits"),
        tool_calls=Sum("tool_calls_count"),
        active_users=Count("user", distinct=True),
    )
    completed_7d = usage_7d.filter(status=AIUsageEvent.Status.COMPLETED)
    completed_count_7d = completed_7d.count()
    cost_7d = usage_aggregates_7d["estimated_cost_usd"] or Decimal("0")

    by_action_type_7d = list(
        usage_7d.values("action_type")
        .annotate(
            events=Count("id"),
            completed=Count("id", filter=Q(status=AIUsageEvent.Status.COMPLETED)),
            errors=Count("id", filter=Q(status=AIUsageEvent.Status.ERROR)),
            blocked=Count("id", filter=Q(status=AIUsageEvent.Status.BLOCKED)),
            total_tokens=Sum("total_tokens"),
            estimated_cost_usd=Sum("estimated_cost_usd"),
            charged_credits=Sum("charged_credits"),
            tool_calls=Sum("tool_calls_count"),
        )
        .order_by("-estimated_cost_usd", "-total_tokens", "-events")[:top_limit]
    )

    by_provider_model_7d = list(
        usage_7d.values("provider", "model_name")
        .annotate(
            events=Count("id"),
            total_tokens=Sum("total_tokens"),
            estimated_cost_usd=Sum("estimated_cost_usd"),
            charged_credits=Sum("charged_credits"),
            avg_latency_ms=Avg("latency_ms"),
        )
        .order_by("-estimated_cost_usd", "-total_tokens", "-events")[:top_limit]
    )

    by_credit_plan_7d = list(
        usage_7d.values("credit_plan_code")
        .annotate(
            events=Count("id"),
            charged_credits=Sum("charged_credits"),
            estimated_cost_usd=Sum("estimated_cost_usd"),
            active_users=Count("user", distinct=True),
        )
        .order_by("-charged_credits", "-estimated_cost_usd", "credit_plan_code")[:top_limit]
    )

    top_users_7d = list(
        usage_7d.filter(user__isnull=False)
        .values("user_id", "user__email", "user__username")
        .annotate(
            events=Count("id"),
            total_tokens=Sum("total_tokens"),
            estimated_cost_usd=Sum("estimated_cost_usd"),
            charged_credits=Sum("charged_credits"),
            blocked=Count("id", filter=Q(status=AIUsageEvent.Status.BLOCKED)),
            errors=Count("id", filter=Q(status=AIUsageEvent.Status.ERROR)),
        )
        .order_by("-estimated_cost_usd", "-total_tokens", "-charged_credits")[:top_limit]
    )

    quotas = list_account_ai_credit_quotas(
        period=period,
        user_segment=analytics_filters.user_segment,
    )
    quota_pressure_rows: list[dict] = []
    for quota in quotas:
        if quota.monthly_credit_limit <= 0:
            continue
        quota_pressure_rows.append(
            {
                "email": quota.user.email or quota.user.get_username(),
                "username": quota.user.get_username(),
                "plan_code": quota.plan_code,
                "credits_used": quota.credits_used,
                "monthly_credit_limit": quota.monthly_credit_limit,
                "daily_credit_limit": quota.daily_credit_limit,
                "usage_ratio": quota.usage_ratio,
                "hard_blocked": quota.hard_blocked,
            }
        )
    quota_pressure_rows.sort(key=lambda row: (row["hard_blocked"], row["usage_ratio"], row["credits_used"]), reverse=True)

    credit_ledger_7d = analytics_filters.apply_user_segment(
        CreditLedger.objects.filter(
            created_at__gte=since_7d,
            reference_type=AI_CREDIT_REFERENCE_TYPE,
        ),
        "user",
    )
    credit_ledger_by_kind_7d = list(
        credit_ledger_7d.values("kind")
        .annotate(entries=Count("id"), credits=Sum("credits_delta"))
        .order_by("kind")
    )

    ai_proposals = analytics_filters.apply_user_segment(NutritionProposal.objects.filter(source=NutritionProposal.SOURCE_AI), "created_by")
    ai_proposals_7d = ai_proposals.filter(created_at__gte=since_7d)
    applied_proposals_7d = ai_proposals.filter(status=NutritionProposal.STATUS_APPLIED, applied_at__gte=since_7d)
    chats = analytics_filters.apply_user_segment(AiNutritionChat.objects.all(), "user")

    return {
        "generated_at": now,
        "period_label": analytics_filters.period_label,
        "current_period": period,
        "usage": {
            "events_total": usage.count(),
            "events_7d": usage_7d.count(),
            "events_30d": usage_30d.count(),
            "active_users_7d": usage_aggregates_7d["active_users"] or 0,
            "completed_7d": completed_count_7d,
            "error_7d": usage_7d.filter(status=AIUsageEvent.Status.ERROR).count(),
            "blocked_7d": usage_7d.filter(status=AIUsageEvent.Status.BLOCKED).count(),
            "tool_calls_7d": usage_aggregates_7d["tool_calls"] or 0,
            "events_with_tools_7d": usage_7d.filter(tool_calls_count__gt=0).count(),
            "total_tokens_7d": usage_aggregates_7d["total_tokens"] or 0,
            "input_tokens_7d": usage_aggregates_7d["input_tokens"] or 0,
            "cached_input_tokens_7d": usage_aggregates_7d["cached_input_tokens"] or 0,
            "output_tokens_7d": usage_aggregates_7d["output_tokens"] or 0,
            "estimated_cost_usd_7d": cost_7d,
            "avg_cost_per_completed_turn_7d": (cost_7d / Decimal(completed_count_7d)) if completed_count_7d else Decimal("0"),
            "avg_latency_ms_7d": _avg(usage_7d, "latency_ms"),
            "charged_credits_7d": usage_aggregates_7d["charged_credits"] or 0,
        },
        "breakdowns": {
            "by_action_type_7d": by_action_type_7d,
            "by_provider_model_7d": by_provider_model_7d,
            "by_credit_plan_7d": by_credit_plan_7d,
            "top_users_7d": top_users_7d,
        },
        "credits": {
            "quota_rows": quota_pressure_rows[:top_limit],
            "quotas_total": len(quotas),
            "hard_blocked_quotas": sum(1 for quota in quotas if quota.hard_blocked),
            "ledger_entries_7d": credit_ledger_7d.count(),
            "ledger_credits_7d": abs(_sum(credit_ledger_7d.filter(kind=CreditLedger.Kind.CONSUME), "credits_delta")),
            "ledger_by_kind_7d": credit_ledger_by_kind_7d,
        },
        "outcomes": {
            "ai_proposals_total": ai_proposals.count(),
            "ai_proposals_7d": ai_proposals_7d.count(),
            "pending_review_7d": ai_proposals_7d.filter(status=NutritionProposal.STATUS_PENDING_REVIEW).count(),
            "rejected_7d": ai_proposals_7d.filter(status=NutritionProposal.STATUS_REJECTED).count(),
            "applied_7d": applied_proposals_7d.count(),
            "applied_total": ai_proposals.filter(status=NutritionProposal.STATUS_APPLIED).count(),
            "chats_total": chats.count(),
            "active_chats": chats.filter(status=AiNutritionChat.STATUS_ACTIVE).count(),
            "proposal_chats": chats.filter(status=AiNutritionChat.STATUS_PROPOSAL_CREATED).count(),
        },
    }
