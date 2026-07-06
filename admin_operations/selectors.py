from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, Q, Sum
from django.utils import timezone

from accounts.models import AccountSubscription, CreditLedger, CreditWallet
from ai_assistant.models import AIUsageEvent, AIUserCreditQuota
from food_catalog.models import CatalogCurationCandidate, CatalogFood
from notas.domain.model_modules.proposals import NutritionProposal
from admin_operations.models import AdminOperationAuditEvent

CATALOG_CANDIDATE_ACTION_STATUSES = [
    CatalogCurationCandidate.STATUS_QUEUED,
    CatalogCurationCandidate.STATUS_IN_REVIEW,
    CatalogCurationCandidate.STATUS_NEEDS_MORE_EVIDENCE,
]

CATALOG_FOOD_REVIEW_STATUSES = [
    CatalogFood.STATUS_EXTERNAL_CANDIDATE,
    CatalogFood.STATUS_MANUAL_CANDIDATE,
    CatalogFood.STATUS_BRAND_SUBMITTED,
    CatalogFood.STATUS_NORMALIZED,
    CatalogFood.STATUS_PENDING_REVIEW,
    CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
]

AI_OPERATIONAL_STATUSES = [
    AIUsageEvent.Status.ERROR,
    AIUsageEvent.Status.BLOCKED,
]


def get_operations_overview_metrics() -> dict:
    now = timezone.now()
    since_7d = now - timedelta(days=7)

    candidate_qs = CatalogCurationCandidate.objects.filter(status__in=CATALOG_CANDIDATE_ACTION_STATUSES)
    catalog_food_qs = CatalogFood.objects.filter(status__in=CATALOG_FOOD_REVIEW_STATUSES)
    ai_issue_qs = AIUsageEvent.objects.filter(status__in=AI_OPERATIONAL_STATUSES, created_at__gte=since_7d)
    proposal_review_qs = NutritionProposal.objects.filter(
        source__in=[NutritionProposal.SOURCE_AI, NutritionProposal.SOURCE_MCP],
        status=NutritionProposal.STATUS_PENDING_REVIEW,
    )
    wallet_qs = CreditWallet.objects.filter(reserved_balance__gt=0)

    catalog = {
        "pending_candidates": candidate_qs.count(),
        "high_priority_candidates": candidate_qs.filter(priority__gte=75).count(),
        "needs_more_evidence_candidates": candidate_qs.filter(
            status=CatalogCurationCandidate.STATUS_NEEDS_MORE_EVIDENCE,
        ).count(),
        "catalog_foods_requiring_review": catalog_food_qs.count(),
    }

    ai = ai_issue_qs.aggregate(
        total=Count("id"),
        errors=Count("id", filter=Q(status=AIUsageEvent.Status.ERROR)),
        blocked=Count("id", filter=Q(status=AIUsageEvent.Status.BLOCKED)),
    )
    ai.update({
        "pending_ai_proposals": proposal_review_qs.count(),
    })

    accounts = wallet_qs.aggregate(
        wallets_with_reserved_credits=Count("id"),
        reserved_credits_total=Sum("reserved_balance"),
    )
    accounts["reserved_credits_total"] = accounts["reserved_credits_total"] or 0

    warnings = _build_warning_candidates(catalog=catalog, ai=ai, accounts=accounts)

    return {
        "generated_at": now,
        "period_label": "Últimos 7 días · señales operacionales",
        "catalog": catalog,
        "ai": ai,
        "accounts": accounts,
        "warnings": warnings,
    }


def get_food_catalog_operations_payload(*, limit: int = 25) -> dict:
    """Return actionable Food Catalog queues for OPS03.

    The payload is deliberately read-model oriented. Mutations are handled by
    explicit services so templates never perform direct model changes.
    """

    candidate_qs = CatalogCurationCandidate.objects.filter(
        status__in=CATALOG_CANDIDATE_ACTION_STATUSES,
    ).select_related("reviewed_by").order_by("-priority", "status", "display_name")

    catalog_food_qs = CatalogFood.objects.filter(
        status__in=CATALOG_FOOD_REVIEW_STATUSES,
    ).order_by("status", "-data_quality_score", "display_name")

    candidate_counts = candidate_qs.aggregate(
        total=Count("id"),
        high_priority=Count("id", filter=Q(priority__gte=75)),
        needs_more_evidence=Count("id", filter=Q(status=CatalogCurationCandidate.STATUS_NEEDS_MORE_EVIDENCE)),
    )
    food_counts = catalog_food_qs.aggregate(
        total=Count("id"),
        pending_review=Count("id", filter=Q(status=CatalogFood.STATUS_PENDING_REVIEW)),
        needs_more_evidence=Count("id", filter=Q(status=CatalogFood.STATUS_NEEDS_MORE_EVIDENCE)),
    )

    return {
        "candidate_counts": candidate_counts,
        "food_counts": food_counts,
        "candidates": list(candidate_qs[:limit]),
        "catalog_foods": list(catalog_food_qs[:limit]),
    }


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


def _build_warning_candidates(*, catalog: dict, ai: dict, accounts: dict) -> list[dict]:
    warnings: list[dict] = []

    if catalog["high_priority_candidates"]:
        warnings.append({
            "severity": "warning",
            "domain": "Food Catalog",
            "title": "Candidatos de alta prioridad",
            "value": catalog["high_priority_candidates"],
            "description": "Hay candidatos de curación con prioridad 75+ esperando revisión staff.",
        })
    elif catalog["pending_candidates"]:
        warnings.append({
            "severity": "info",
            "domain": "Food Catalog",
            "title": "Candidatos pendientes",
            "value": catalog["pending_candidates"],
            "description": "La cola ya tiene work items listos para el workflow OPS03.",
        })

    if ai.get("errors", 0):
        warnings.append({
            "severity": "warning",
            "domain": "AI Assistant",
            "title": "Errores IA recientes",
            "value": ai["errors"],
            "description": "Existen AIUsageEvent con estado error en los últimos 7 días.",
        })

    if ai.get("blocked", 0):
        warnings.append({
            "severity": "warning",
            "domain": "AI Assistant",
            "title": "Eventos IA bloqueados",
            "value": ai["blocked"],
            "description": "Hay turnos bloqueados que podrían requerir revisión de créditos, cuotas o guardrails.",
        })

    if accounts["wallets_with_reserved_credits"]:
        warnings.append({
            "severity": "watch",
            "domain": "Accounts & Credits",
            "title": "Wallets con créditos reservados",
            "value": accounts["wallets_with_reserved_credits"],
            "description": "Existen saldos reservados. OPS04 deberá distinguir reservas sanas vs. atascadas antes de liberar créditos.",
        })

    return warnings



def get_accounts_operations_payload(*, query: str = "", limit: int = 25) -> dict:
    """Return actionable Accounts & Credits queues for OPS04.

    The selector is read-only. Wallet mutations are handled by explicit services
    that append CreditLedger movements instead of editing historical entries.
    """

    normalized_query = (query or "").strip()
    wallet_qs = (
        CreditWallet.objects.select_related("user")
        .order_by("-reserved_balance", "user__email", "user__username")
    )
    if normalized_query:
        wallet_qs = wallet_qs.filter(
            Q(user__email__icontains=normalized_query)
            | Q(user__username__icontains=normalized_query)
            | Q(user__first_name__icontains=normalized_query)
            | Q(user__last_name__icontains=normalized_query)
        )

    reservations_qs = _open_credit_reservations_queryset()
    if normalized_query:
        reservations_qs = reservations_qs.filter(
            Q(user__email__icontains=normalized_query)
            | Q(user__username__icontains=normalized_query)
            | Q(reference_type__icontains=normalized_query)
            | Q(reference_id__icontains=normalized_query)
        )

    wallet_counts = wallet_qs.aggregate(
        total=Count("id"),
        with_reserved=Count("id", filter=Q(reserved_balance__gt=0)),
        reserved_total=Sum("reserved_balance"),
    )
    wallet_counts["reserved_total"] = wallet_counts["reserved_total"] or 0
    open_reservations = reservations_qs.aggregate(
        total=Count("id"),
        reserved_total=Sum("reserved_delta"),
    )
    open_reservations["reserved_total"] = open_reservations["reserved_total"] or 0

    subscriptions = _subscriptions_by_user(wallet_qs[:limit])

    return {
        "query": normalized_query,
        "wallet_counts": wallet_counts,
        "reservation_counts": open_reservations,
        "wallets": list(wallet_qs[:limit]),
        "reservations": list(reservations_qs[:limit]),
        "subscriptions_by_user": subscriptions,
    }


def get_account_detail_payload(*, user_id: int, ledger_limit: int = 30) -> dict:
    User = get_user_model()
    user = User.objects.get(pk=user_id)
    wallet = CreditWallet.objects.select_related("user").filter(user=user).first()
    subscription = (
        AccountSubscription.objects.select_related("plan")
        .filter(user=user)
        .order_by("-created_at")
        .first()
    )
    ledger_entries = []
    reservations = []
    if wallet is not None:
        ledger_entries = list(
            CreditLedger.objects.filter(wallet=wallet)
            .select_related("user")
            .order_by("-created_at", "-id")[:ledger_limit]
        )
        reservations = list(_open_credit_reservations_queryset().filter(wallet=wallet)[:ledger_limit])
    return {
        "user": user,
        "wallet": wallet,
        "subscription": subscription,
        "ledger_entries": ledger_entries,
        "reservations": reservations,
    }


def _open_credit_reservations_queryset():
    closed_references = CreditLedger.objects.filter(
        kind__in=(CreditLedger.Kind.CONSUME, CreditLedger.Kind.RELEASE),
        reference_type__gt="",
        reference_id__gt="",
    ).values_list("reference_type", "reference_id")
    closed_pairs = {(reference_type, reference_id) for reference_type, reference_id in closed_references}

    qs = (
        CreditLedger.objects.select_related("wallet", "user")
        .filter(kind=CreditLedger.Kind.RESERVE, reserved_delta__gt=0)
        .order_by("created_at", "id")
    )
    if not closed_pairs:
        return qs

    closed_q = Q()
    for reference_type, reference_id in closed_pairs:
        closed_q |= Q(reference_type=reference_type, reference_id=reference_id)
    return qs.exclude(closed_q)


def _subscriptions_by_user(wallets) -> dict[int, AccountSubscription]:
    user_ids = [wallet.user_id for wallet in wallets]
    if not user_ids:
        return {}
    subscriptions = (
        AccountSubscription.objects.select_related("plan")
        .filter(user_id__in=user_ids)
        .order_by("user_id", "-created_at")
    )
    result: dict[int, AccountSubscription] = {}
    for subscription in subscriptions:
        result.setdefault(subscription.user_id, subscription)
    return result


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
