from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from admin_operations.models import AdminOperationAuditEvent


def get_audit_log_payload(*, query: str = "", limit: int = 50) -> dict:
    """Return recent Admin Operations audit events for OPS06."""

    normalized_query = (query or "").strip()
    events_qs = AdminOperationAuditEvent.objects.select_related("actor").order_by("-created_at", "-id")
    if normalized_query:
        events_qs = events_qs.filter(
            Q(actor_label__icontains=normalized_query)
            | Q(action__icontains=normalized_query)
            | Q(target_app__icontains=normalized_query)
            | Q(target_model__icontains=normalized_query)
            | Q(target_id__icontains=normalized_query)
            | Q(target_label__icontains=normalized_query)
            | Q(reason__icontains=normalized_query)
        )

    total = events_qs.count()
    recent_24h = events_qs.filter(created_at__gte=timezone.now() - timedelta(days=1)).count()
    financial = events_qs.filter(target_app="accounts").count()
    ai = events_qs.filter(target_app="ai_assistant").count() + events_qs.filter(target_app="notas").count()

    return {
        "query": normalized_query,
        "events": list(events_qs[:limit]),
        "counts": {
            "total": total,
            "recent_24h": recent_24h,
            "financial": financial,
            "ai": ai,
        },
    }


__all__ = ['get_audit_log_payload']
