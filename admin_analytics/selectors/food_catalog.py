from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from admin_analytics.filters import AdminAnalyticsFilters

from food_catalog.models import (
    CatalogCurationCandidate,
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
    CatalogImportBatch,
    ExternalFoodReference,
    ExternalProviderFetchLog,
)


def _avg(queryset, field: str):
    return queryset.aggregate(avg=Avg(field))["avg"] or 0


def _sum(queryset, field: str):
    return queryset.aggregate(total=Sum(field))["total"] or 0


def get_food_catalog_metrics(*, now=None, analytics_filters: AdminAnalyticsFilters | None = None, top_limit: int = 10) -> dict:
    """Return ADM06 read-only Food Catalog quality and curation metrics.

    The selector consumes the master catalog, evidence, external reference,
    curation candidate and import batch tables. It does not write snapshots or
    promote foods into operational `notas.Food`.
    """

    now = now or timezone.now()
    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    since_7d = analytics_filters.since(now=now)
    since_30d = now - timedelta(days=30)

    foods = CatalogFood.objects.all()
    foods_7d = foods.filter(created_at__gte=since_7d)
    foods_30d = foods.filter(created_at__gte=since_30d)
    published_or_verified = foods.filter(
        status__in=[CatalogFood.STATUS_PUBLISHED, CatalogFood.STATUS_VERIFIED]
    )
    active_review_queue = foods.filter(
        status__in=[
            CatalogFood.STATUS_EXTERNAL_CANDIDATE,
            CatalogFood.STATUS_MANUAL_CANDIDATE,
            CatalogFood.STATUS_BRAND_SUBMITTED,
            CatalogFood.STATUS_NORMALIZED,
            CatalogFood.STATUS_PENDING_REVIEW,
            CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
            CatalogFood.STATUS_REVIEWED,
        ]
    )

    missing_macro = foods.filter(
        Q(protein_g_per_100g__isnull=True)
        | Q(carbs_g_per_100g__isnull=True)
        | Q(fat_g_per_100g__isnull=True)
    )
    missing_optional_nutrients = foods.filter(
        Q(calories_kcal_per_100g__isnull=True)
        | Q(fiber_g_per_100g__isnull=True)
        | Q(sodium_mg_per_100g__isnull=True)
    )
    low_quality = foods.filter(data_quality_score__lt=60)
    needs_more_evidence = foods.filter(status=CatalogFood.STATUS_NEEDS_MORE_EVIDENCE)
    rejected_archived = foods.filter(status__in=[CatalogFood.STATUS_REJECTED, CatalogFood.STATUS_ARCHIVED])

    foods_with_relations = foods.annotate(
        portions_count=Count("portions", distinct=True),
        aliases_count=Count("aliases", distinct=True),
        sources_count=Count("sources", distinct=True),
    )
    foods_without_sources = foods_with_relations.filter(sources_count=0)
    foods_without_portions = foods_with_relations.filter(portions_count=0)
    foods_without_aliases = foods_with_relations.filter(aliases_count=0)

    status_rows = list(
        foods.values("status")
        .annotate(
            total=Count("id"),
            created_7d=Count("id", filter=Q(created_at__gte=since_7d)),
            avg_quality=Avg("data_quality_score"),
            solver_enabled=Count("id", filter=Q(solver_enabled=True)),
        )
        .order_by("status")
    )

    source_rows = list(
        foods.values("source_type")
        .annotate(
            total=Count("id"),
            created_7d=Count("id", filter=Q(created_at__gte=since_7d)),
            avg_quality=Avg("data_quality_score"),
            published=Count("id", filter=Q(status=CatalogFood.STATUS_PUBLISHED)),
        )
        .order_by("source_type")
    )

    evidence_rows = [
        {
            "label": "Portions",
            "total": CatalogFoodPortion.objects.count(),
            "foods_missing": foods_without_portions.count(),
            "created_7d": CatalogFoodPortion.objects.filter(created_at__gte=since_7d).count(),
        },
        {
            "label": "Aliases",
            "total": CatalogFoodAlias.objects.count(),
            "foods_missing": foods_without_aliases.count(),
            "created_7d": CatalogFoodAlias.objects.filter(created_at__gte=since_7d).count(),
        },
        {
            "label": "Sources",
            "total": CatalogFoodSource.objects.count(),
            "foods_missing": foods_without_sources.count(),
            "created_7d": CatalogFoodSource.objects.filter(imported_at__gte=since_7d).count(),
        },
    ]

    license_rows = list(
        CatalogFoodSource.objects.values("license_status")
        .annotate(total=Count("id"), foods=Count("catalog_food", distinct=True))
        .order_by("license_status")
    )

    batches = CatalogImportBatch.objects.all()
    batches_7d = batches.filter(started_at__gte=since_7d)
    batch_status_rows = list(
        batches.values("status")
        .annotate(
            total=Count("id"),
            rows=Sum("total_rows"),
            imported=Sum("imported_rows"),
            skipped=Sum("skipped_rows"),
            failed=Sum("failed_rows"),
        )
        .order_by("status")
    )
    batch_source_rows = list(
        batches.values("source_type")
        .annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=CatalogImportBatch.STATUS_COMPLETED)),
            failed=Count("id", filter=Q(status=CatalogImportBatch.STATUS_FAILED)),
            imported=Sum("imported_rows"),
            failed_rows=Sum("failed_rows"),
        )
        .order_by("source_type")
    )

    external_refs = ExternalFoodReference.objects.all()
    external_refs_7d = external_refs.filter(first_seen_at__gte=since_7d)
    expired_refs = external_refs.filter(expires_at__lt=now)
    provider_reference_rows = list(
        external_refs.values("provider")
        .annotate(
            references=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
            selected=Sum("selected_count"),
            seen=Sum("seen_count"),
            expired=Count("id", filter=Q(expires_at__lt=now)),
        )
        .order_by("provider")
    )

    fetch_logs = ExternalProviderFetchLog.objects.all()
    fetch_logs_7d = fetch_logs.filter(fetched_at__gte=since_7d)
    provider_fetch_rows = list(
        fetch_logs_7d.values("provider", "lookup_type")
        .annotate(
            total=Count("id"),
            success=Count("id", filter=Q(status=ExternalProviderFetchLog.STATUS_SUCCESS)),
            failed=Count("id", filter=Q(status=ExternalProviderFetchLog.STATUS_FAILED)),
        )
        .order_by("provider", "lookup_type")[:top_limit]
    )

    candidates = CatalogCurationCandidate.objects.all()
    candidate_rows = list(
        candidates.values("status")
        .annotate(
            total=Count("id"),
            avg_priority=Avg("priority"),
            created_7d=Count("id", filter=Q(created_at__gte=since_7d)),
        )
        .order_by("status")
    )
    candidate_reason_rows = list(
        candidates.values("reason")
        .annotate(total=Count("id"), avg_priority=Avg("priority"))
        .order_by("reason")
    )

    return {
        "generated_at": now,
        "period_label": analytics_filters.period_label,
        "catalog": {
            "foods_total": foods.count(),
            "foods_7d": foods_7d.count(),
            "foods_30d": foods_30d.count(),
            "published": foods.filter(status=CatalogFood.STATUS_PUBLISHED).count(),
            "verified": foods.filter(status=CatalogFood.STATUS_VERIFIED).count(),
            "published_or_verified": published_or_verified.count(),
            "review_queue": active_review_queue.count(),
            "solver_enabled": foods.filter(solver_enabled=True).count(),
            "branded": foods.filter(is_branded=True).count(),
            "avg_quality_score": _avg(foods, "data_quality_score"),
            "missing_macro": missing_macro.count(),
            "missing_optional_nutrients": missing_optional_nutrients.count(),
            "low_quality": low_quality.count(),
            "needs_more_evidence": needs_more_evidence.count(),
            "rejected_archived": rejected_archived.count(),
            "status_rows": status_rows,
            "source_rows": source_rows,
        },
        "evidence": {
            "portions_total": CatalogFoodPortion.objects.count(),
            "aliases_total": CatalogFoodAlias.objects.count(),
            "sources_total": CatalogFoodSource.objects.count(),
            "foods_without_sources": foods_without_sources.count(),
            "foods_without_portions": foods_without_portions.count(),
            "foods_without_aliases": foods_without_aliases.count(),
            "rows": evidence_rows,
            "license_rows": license_rows,
        },
        "imports": {
            "batches_total": batches.count(),
            "batches_7d": batches_7d.count(),
            "completed": batches.filter(status=CatalogImportBatch.STATUS_COMPLETED).count(),
            "failed": batches.filter(status=CatalogImportBatch.STATUS_FAILED).count(),
            "running_or_pending": batches.filter(
                status__in=[CatalogImportBatch.STATUS_PENDING, CatalogImportBatch.STATUS_RUNNING]
            ).count(),
            "total_rows": _sum(batches, "total_rows"),
            "imported_rows": _sum(batches, "imported_rows"),
            "failed_rows": _sum(batches, "failed_rows"),
            "status_rows": batch_status_rows,
            "source_rows": batch_source_rows,
        },
        "external": {
            "references_total": external_refs.count(),
            "references_7d": external_refs_7d.count(),
            "active_references": external_refs.filter(is_active=True).count(),
            "expired_references": expired_refs.count(),
            "selected_count": _sum(external_refs, "selected_count"),
            "seen_count": _sum(external_refs, "seen_count"),
            "fetch_logs_7d": fetch_logs_7d.count(),
            "fetch_success_7d": fetch_logs_7d.filter(status=ExternalProviderFetchLog.STATUS_SUCCESS).count(),
            "fetch_failed_7d": fetch_logs_7d.filter(status=ExternalProviderFetchLog.STATUS_FAILED).count(),
            "provider_reference_rows": provider_reference_rows,
            "provider_fetch_rows": provider_fetch_rows,
        },
        "curation": {
            "candidates_total": candidates.count(),
            "candidates_7d": candidates.filter(created_at__gte=since_7d).count(),
            "queued": candidates.filter(status=CatalogCurationCandidate.STATUS_QUEUED).count(),
            "in_review": candidates.filter(status=CatalogCurationCandidate.STATUS_IN_REVIEW).count(),
            "needs_more_evidence": candidates.filter(status=CatalogCurationCandidate.STATUS_NEEDS_MORE_EVIDENCE).count(),
            "approved_for_curation": candidates.filter(status=CatalogCurationCandidate.STATUS_APPROVED_FOR_CURATION).count(),
            "rejected": candidates.filter(status=CatalogCurationCandidate.STATUS_REJECTED).count(),
            "avg_priority": _avg(candidates, "priority"),
            "status_rows": candidate_rows,
            "reason_rows": candidate_reason_rows,
        },
    }
