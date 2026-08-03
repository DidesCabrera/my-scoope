from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.db.models import Count, Q
from django.utils import timezone

from ai_assistant.models import AIUsageEvent, AIUserCreditQuota
from notas.domain.model_modules.proposals import NutritionProposal

from admin_operations.selector_modules.constants import AI_OPERATIONAL_STATUSES

def get_ai_operations_payload(*, query: str = "", limit: int = 25) -> dict:
    """Return actionable AI Assistant queues for OPS05.

    OPS05 deliberately focuses on existing records: recent AIUsageEvent issues,
    AI/MCP NutritionProposal records awaiting staff review, and AI credit quotas
    that may explain blocked access.
    """

    normalized_query = (query or "").strip()
    since_7d = timezone.now() - timedelta(days=7)

    event_qs = (
        AIUsageEvent.objects.select_related("user")
        .filter(status__in=AI_OPERATIONAL_STATUSES, created_at__gte=since_7d)
        .order_by("-created_at", "-id")
    )
    proposal_qs = (
        NutritionProposal.objects.select_related("created_by", "dailyplan")
        .filter(
            source__in=[NutritionProposal.SOURCE_AI, NutritionProposal.SOURCE_MCP],
            status=NutritionProposal.STATUS_PENDING_REVIEW,
        )
        .order_by("-created_at", "-id")
    )
    quota_qs = (
        AIUserCreditQuota.objects.select_related("user")
        .filter(Q(hard_blocked=True) | Q(credits_used__gte=models.F("monthly_credit_limit")))
        .order_by("-hard_blocked", "-updated_at", "user__email", "user__username")
    )

    if normalized_query:
        user_filter = (
            Q(user__email__icontains=normalized_query)
            | Q(user__username__icontains=normalized_query)
            | Q(user__first_name__icontains=normalized_query)
            | Q(user__last_name__icontains=normalized_query)
        )
        event_qs = event_qs.filter(
            user_filter
            | Q(action_type__icontains=normalized_query)
            | Q(error_type__icontains=normalized_query)
            | Q(provider__icontains=normalized_query)
            | Q(model_name__icontains=normalized_query)
            | Q(conversation_id__icontains=normalized_query)
            | Q(turn_id__icontains=normalized_query)
        )
        proposal_qs = proposal_qs.filter(
            Q(created_by__email__icontains=normalized_query)
            | Q(created_by__username__icontains=normalized_query)
            | Q(title__icontains=normalized_query)
            | Q(summary__icontains=normalized_query)
            | Q(source__icontains=normalized_query)
        )
        quota_qs = quota_qs.filter(
            user_filter
            | Q(plan_code__icontains=normalized_query)
            | Q(period__icontains=normalized_query)
        )

    event_counts = event_qs.aggregate(
        total=Count("id"),
        errors=Count("id", filter=Q(status=AIUsageEvent.Status.ERROR)),
        blocked=Count("id", filter=Q(status=AIUsageEvent.Status.BLOCKED)),
    )
    proposal_counts = proposal_qs.aggregate(
        total=Count("id"),
        ai=Count("id", filter=Q(source=NutritionProposal.SOURCE_AI)),
        mcp=Count("id", filter=Q(source=NutritionProposal.SOURCE_MCP)),
    )
    quota_counts = quota_qs.aggregate(
        total=Count("id"),
        hard_blocked=Count("id", filter=Q(hard_blocked=True)),
    )

    return {
        "query": normalized_query,
        "event_counts": event_counts,
        "proposal_counts": proposal_counts,
        "quota_counts": quota_counts,
        "events": list(event_qs[:limit]),
        "proposals": list(proposal_qs[:limit]),
        "quotas": list(quota_qs[:limit]),
    }




__all__ = ['get_ai_operations_payload']
