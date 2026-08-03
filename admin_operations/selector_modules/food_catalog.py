from __future__ import annotations

from pathlib import Path

from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q

from food_catalog.application.coverage_manifest import load_coverage_manifest
from food_catalog.models import CatalogCurationCandidate, CatalogFood, CatalogFoodSource, CatalogImportBatch

from admin_operations.selector_modules.constants import (
    CATALOG_CANDIDATE_ACTION_STATUSES,
    CATALOG_FOOD_REVIEW_STATUSES,
    CATALOG_GROUP_FAMILIES,
)

def get_food_catalog_operations_payload(*, query: str = "", stage: str = "all", limit: int = 50) -> dict:
    """Return actionable Food Catalog queues for OPS03.

    The payload is deliberately read-model oriented. Mutations are handled by
    explicit services so templates never perform direct model changes.
    """

    normalized_query = (query or "").strip()
    normalized_stage = stage if stage in {
        "all", "intake", "preparation", "review", "publication", "activation", "blocked"
    } else "all"

    candidate_qs = CatalogCurationCandidate.objects.filter(
        status__in=CATALOG_CANDIDATE_ACTION_STATUSES,
    ).select_related("reviewed_by").order_by("-priority", "status", "display_name")

    catalog_food_qs = CatalogFood.objects.filter(
        status__in=CATALOG_FOOD_REVIEW_STATUSES,
    ).prefetch_related("sources", "portions").order_by("status", "-data_quality_score", "display_name")

    if normalized_query:
        candidate_qs = candidate_qs.filter(
            Q(display_name__icontains=normalized_query)
            | Q(brand_name__icontains=normalized_query)
            | Q(provider__icontains=normalized_query)
        )
        catalog_food_qs = catalog_food_qs.filter(
            Q(display_name__icontains=normalized_query)
            | Q(canonical_name__icontains=normalized_query)
            | Q(brand_name__icontains=normalized_query)
            | Q(source_type__icontains=normalized_query)
        )

    catalog_food_count_qs = catalog_food_qs

    candidate_counts = candidate_qs.aggregate(
        total=Count("id"),
        high_priority=Count("id", filter=Q(priority__gte=75)),
        intake=Count("id", filter=Q(status__in=[
            CatalogCurationCandidate.STATUS_QUEUED,
            CatalogCurationCandidate.STATUS_IN_REVIEW,
        ])),
        preparation=Count("id", filter=Q(status=CatalogCurationCandidate.STATUS_APPROVED_FOR_CURATION)),
        needs_more_evidence=Count("id", filter=Q(status=CatalogCurationCandidate.STATUS_NEEDS_MORE_EVIDENCE)),
    )
    food_counts = catalog_food_qs.aggregate(
        total=Count("id"),
        preparation=Count("id", filter=Q(status__in=[
            CatalogFood.STATUS_EXTERNAL_CANDIDATE,
            CatalogFood.STATUS_MANUAL_CANDIDATE,
            CatalogFood.STATUS_BRAND_SUBMITTED,
            CatalogFood.STATUS_NORMALIZED,
        ])),
        pending_review=Count("id", filter=Q(status=CatalogFood.STATUS_PENDING_REVIEW)),
        publication=Count("id", filter=Q(status__in=[CatalogFood.STATUS_REVIEWED, CatalogFood.STATUS_VERIFIED])),
        published=Count("id", filter=Q(status=CatalogFood.STATUS_PUBLISHED)),
        needs_more_evidence=Count("id", filter=Q(status=CatalogFood.STATUS_NEEDS_MORE_EVIDENCE)),
    )

    candidate_stage_statuses = {
        "intake": [CatalogCurationCandidate.STATUS_QUEUED, CatalogCurationCandidate.STATUS_IN_REVIEW],
        "preparation": [CatalogCurationCandidate.STATUS_APPROVED_FOR_CURATION],
        "blocked": [CatalogCurationCandidate.STATUS_NEEDS_MORE_EVIDENCE],
    }
    catalog_food_stage_statuses = {
        "preparation": [
            CatalogFood.STATUS_EXTERNAL_CANDIDATE,
            CatalogFood.STATUS_MANUAL_CANDIDATE,
            CatalogFood.STATUS_BRAND_SUBMITTED,
            CatalogFood.STATUS_NORMALIZED,
        ],
        "review": [CatalogFood.STATUS_PENDING_REVIEW],
        "publication": [CatalogFood.STATUS_REVIEWED, CatalogFood.STATUS_VERIFIED],
        "activation": [CatalogFood.STATUS_PUBLISHED],
        "blocked": [CatalogFood.STATUS_NEEDS_MORE_EVIDENCE],
    }

    if normalized_stage != "all":
        candidate_statuses = candidate_stage_statuses.get(normalized_stage)
        catalog_food_statuses = catalog_food_stage_statuses.get(normalized_stage)
        candidate_qs = (
            candidate_qs.filter(status__in=candidate_statuses)
            if candidate_statuses
            else candidate_qs.none()
        )
        catalog_food_qs = (
            catalog_food_qs.filter(status__in=catalog_food_statuses)
            if catalog_food_statuses
            else catalog_food_qs.none()
        )

    return {
        "query": normalized_query,
        "stage": normalized_stage,
        "candidate_counts": candidate_counts,
        "food_counts": food_counts,
        "candidates": list(candidate_qs[:limit]),
        "catalog_foods": list(catalog_food_qs[:limit]),
        "published_food_ids": list(
            catalog_food_count_qs.filter(status=CatalogFood.STATUS_PUBLISHED).values_list("id", flat=True)
        ),
    }


def get_food_catalog_inventory_payload(
    *,
    query: str = "",
    status: str = "",
    source_type: str = "",
    food_group: str = "",
    solver_state: str = "",
    page: int | str = 1,
    page_size: int = 50,
) -> dict:
    """Return the complete, read-only Food Catalog observability payload."""

    normalized_query = (query or "").strip()
    normalized_status = status if status in dict(CatalogFood.STATUS_CHOICES) else ""
    normalized_source = source_type if source_type in dict(CatalogFood.SOURCE_TYPE_CHOICES) else ""
    normalized_group = (food_group or "").strip()
    normalized_solver = solver_state if solver_state in {"enabled", "disabled"} else ""

    all_foods = CatalogFood.objects.all()
    inventory_qs = (
        all_foods.select_related("created_by", "reviewed_by")
        .prefetch_related("sources", "portions", "aliases")
        .order_by("display_name", "brand_name", "country", "id")
    )

    if normalized_query:
        inventory_qs = inventory_qs.filter(
            Q(display_name__icontains=normalized_query)
            | Q(canonical_name__icontains=normalized_query)
            | Q(brand_name__icontains=normalized_query)
            | Q(food_group__icontains=normalized_query)
            | Q(food_subgroup__icontains=normalized_query)
            | Q(sources__source_name__icontains=normalized_query)
            | Q(sources__source_food_id__icontains=normalized_query)
        ).distinct()
    if normalized_status:
        inventory_qs = inventory_qs.filter(status=normalized_status)
    if normalized_source:
        inventory_qs = inventory_qs.filter(source_type=normalized_source)
    if normalized_group:
        inventory_qs = inventory_qs.filter(food_group=normalized_group)
    if normalized_solver:
        inventory_qs = inventory_qs.filter(solver_enabled=normalized_solver == "enabled")

    aggregate = all_foods.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=CatalogFood.STATUS_PUBLISHED)),
        solver_enabled=Count("id", filter=Q(solver_enabled=True)),
        average_quality=Avg("data_quality_score"),
        average_protein=Avg("protein_g_per_100g"),
        average_carbs=Avg("carbs_g_per_100g"),
        average_fat=Avg("fat_g_per_100g"),
        average_fiber=Avg("fiber_g_per_100g"),
        missing_group=Count("id", filter=Q(food_group="")),
        incomplete_extended_nutrition=Count(
            "id",
            filter=(
                Q(calories_kcal_per_100g__isnull=True)
                | Q(fiber_g_per_100g__isnull=True)
                | Q(sugar_g_per_100g__isnull=True)
                | Q(saturated_fat_g_per_100g__isnull=True)
                | Q(sodium_mg_per_100g__isnull=True)
            ),
            distinct=True,
        ),
        unknown_culinary_semantics=Count(
            "id",
            filter=(
                Q(preparation_state=CatalogFood.PREPARATION_UNKNOWN)
                | Q(food_form=CatalogFood.FOOD_FORM_UNKNOWN)
            ),
        ),
    )
    aggregate["without_evidence"] = all_foods.filter(sources__isnull=True).count()

    group_rows = list(
        all_foods.values("food_group")
        .annotate(
            total=Count("id"),
            published=Count("id", filter=Q(status=CatalogFood.STATUS_PUBLISHED)),
            solver_enabled=Count("id", filter=Q(solver_enabled=True)),
            average_quality=Avg("data_quality_score"),
        )
        .order_by("food_group")
    )
    category_coverage = _catalog_category_coverage(group_rows)
    source_breakdown = list(
        all_foods.values("source_type")
        .annotate(
            total=Count("id"),
            published=Count("id", filter=Q(status=CatalogFood.STATUS_PUBLISHED)),
            solver_enabled=Count("id", filter=Q(solver_enabled=True)),
            average_quality=Avg("data_quality_score"),
        )
        .order_by("-total", "source_type")
    )

    groups = list(
        all_foods.exclude(food_group="")
        .order_by("food_group")
        .values_list("food_group", flat=True)
        .distinct()
    )
    paginator = Paginator(inventory_qs, page_size)
    page_obj = paginator.get_page(page)

    return {
        "query": normalized_query,
        "status": normalized_status,
        "source_type": normalized_source,
        "food_group": normalized_group,
        "solver_state": normalized_solver,
        "aggregate": aggregate,
        "category_coverage": category_coverage,
        "source_breakdown": source_breakdown,
        "group_rows": group_rows,
        "status_options": CatalogFood.STATUS_CHOICES,
        "source_options": CatalogFood.SOURCE_TYPE_CHOICES,
        "group_options": groups,
        "page_obj": page_obj,
        "filtered_total": paginator.count,
        "generic_coverage": get_generic_food_coverage_payload(),
    }


def get_generic_food_coverage_payload() -> dict:
    """Reconcile the versioned planning manifest with persisted source evidence."""

    manifest = load_coverage_manifest(
        Path(__file__).resolve().parents[2]
        / "food_catalog"
        / "data"
        / "generic_food_coverage_manifest_v1.csv",
        version="gfc.v1",
    )
    mapped_targets = [target for target in manifest.targets if target.mapping_status == "mapped"]
    source_rows = CatalogFoodSource.objects.filter(
        source_food_id__in=[target.source_food_id for target in mapped_targets]
    ).select_related("catalog_food")
    foods_by_source = {
        (row.source_type, row.source_food_id): row.catalog_food
        for row in source_rows
    }

    def persisted_food(target):
        source_type = (
            CatalogFood.SOURCE_NATURAL_VERIFIED
            if target.expected_source == "internal_seed"
            else CatalogFood.SOURCE_USDA
        )
        return foods_by_source.get((source_type, target.source_food_id))

    imported_targets = [(target, persisted_food(target)) for target in mapped_targets]
    imported_targets = [(target, food) for target, food in imported_targets if food is not None]
    reviewed_statuses = {
        CatalogFood.STATUS_REVIEWED,
        CatalogFood.STATUS_VERIFIED,
        CatalogFood.STATUS_PUBLISHED,
    }
    category_rows = []
    for category, defined in manifest.counts_by_category().items():
        imported = sum(1 for target, _food in imported_targets if target.category == category)
        category_rows.append({"key": category, "defined": defined, "imported": imported})

    return {
        "version": manifest.version,
        "sha256": manifest.sha256,
        "total": manifest.total_targets,
        "source_mapped": len(mapped_targets),
        "imported": len(imported_targets),
        "reviewed": sum(1 for _target, food in imported_targets if food.status in reviewed_statuses),
        "published": sum(
            1 for _target, food in imported_targets if food.status == CatalogFood.STATUS_PUBLISHED
        ),
        "category_rows": category_rows,
    }


def get_food_catalog_import_batches_payload(*, source_type: str = "", status: str = "", limit: int = 100) -> dict:
    """Return governed dry-runs and imports without exposing source payloads."""

    normalized_source = source_type if source_type in dict(CatalogFood.SOURCE_TYPE_CHOICES) else ""
    normalized_status = status if status in dict(CatalogImportBatch.STATUS_CHOICES) else ""
    queryset = CatalogImportBatch.objects.select_related("requested_by", "dry_run_batch").order_by("-started_at", "-id")
    if normalized_source:
        queryset = queryset.filter(source_type=normalized_source)
    if normalized_status:
        queryset = queryset.filter(status=normalized_status)

    aggregate = CatalogImportBatch.objects.aggregate(
        total=Count("id"),
        dry_runs=Count("id", filter=Q(is_dry_run=True)),
        imports=Count("id", filter=Q(is_dry_run=False)),
        failed=Count(
            "id",
            filter=Q(status__in=[CatalogImportBatch.STATUS_FAILED, CatalogImportBatch.STATUS_COMPLETED_WITH_ERRORS]),
        ),
    )
    orphan_applies = CatalogImportBatch.objects.filter(is_dry_run=False, dry_run_batch__isnull=True).count()
    return {
        "source_type": normalized_source,
        "status": normalized_status,
        "aggregate": aggregate,
        "orphan_applies": orphan_applies,
        "batches": list(queryset[:limit]),
        "source_options": CatalogFood.SOURCE_TYPE_CHOICES,
        "status_options": CatalogImportBatch.STATUS_CHOICES,
    }


def _catalog_category_coverage(group_rows: list[dict]) -> list[dict]:
    family_by_alias = {
        alias.casefold(): key
        for key, _label, aliases in CATALOG_GROUP_FAMILIES
        for alias in aliases
    }
    totals = {
        key: {"key": key, "label": label, "total": 0, "published": 0, "solver_enabled": 0}
        for key, label, _aliases in CATALOG_GROUP_FAMILIES
    }
    recognized_total = 0

    for row in group_rows:
        raw_group = str(row["food_group"] or "").strip()
        family = family_by_alias.get(raw_group.casefold())
        if not family:
            continue
        recognized_total += int(row["total"] or 0)
        totals[family]["total"] += int(row["total"] or 0)
        totals[family]["published"] += int(row["published"] or 0)
        totals[family]["solver_enabled"] += int(row["solver_enabled"] or 0)

    result = list(totals.values())
    result.append({
        "key": "unmapped",
        "label": "Sin taxonomía estándar",
        "total": max(sum(int(row["total"] or 0) for row in group_rows) - recognized_total, 0),
        "published": 0,
        "solver_enabled": 0,
    })
    return result




__all__ = ['get_food_catalog_operations_payload', 'get_food_catalog_inventory_payload', 'get_generic_food_coverage_payload', 'get_food_catalog_import_batches_payload']
