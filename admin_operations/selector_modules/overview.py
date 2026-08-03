from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from accounts.models import CreditWallet
from ai_assistant.models import AIUsageEvent
from billing.models import BillingEvent, ProviderSubscription, TaxDocument
from food_catalog.models import CatalogCurationCandidate, CatalogFood
from notas.domain.model_modules.proposals import NutritionProposal

from admin_operations.selector_modules.common import _build_warning_candidates
from admin_operations.selector_modules.constants import (
    AI_OPERATIONAL_STATUSES,
    CATALOG_CANDIDATE_ACTION_STATUSES,
    CATALOG_FOOD_REVIEW_STATUSES,
)

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
    billing = {
        "failed_events": BillingEvent.objects.filter(status=BillingEvent.Status.FAILED).count(),
        "past_due_subscriptions": ProviderSubscription.objects.filter(status=ProviderSubscription.Status.PAST_DUE).count(),
        "failed_tax_documents": TaxDocument.objects.filter(status__in=[TaxDocument.Status.FAILED, TaxDocument.Status.REJECTED]).count(),
        "tax_adjustments": TaxDocument.objects.filter(adjustment_required=True).count(),
    }

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
        "billing": billing,
        "warnings": warnings,
    }




__all__ = ['get_operations_overview_metrics']
