"""Curation candidate queue for external food references.

External provider references can show demand, but they are not curated master
foods and are not operational foods. This module creates curator-facing queue
entries so frequently seen or selected external foods can later be reviewed with
proper sources, licensing and normalization before becoming ``CatalogFood``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from food_catalog.models import CatalogCurationCandidate, ExternalFoodReference

DEFAULT_MIN_SELECTED_COUNT = 1
DEFAULT_MIN_SEEN_COUNT = 3
DEFAULT_SELECTED_PRIORITY = 80
DEFAULT_DEMAND_PRIORITY = 60


@dataclass(frozen=True)
class CurationCandidateQueueResult:
    """Result of queueing one external reference for curation."""

    candidate: CatalogCurationCandidate
    created: bool


@dataclass(frozen=True)
class CurationCandidateBulkQueueResult:
    """Summary for queueing external references in bulk."""

    created_count: int
    updated_count: int
    skipped_count: int
    candidate_ids: tuple[int, ...]


def should_queue_external_reference(
    reference: ExternalFoodReference,
    *,
    min_selected_count: int = DEFAULT_MIN_SELECTED_COUNT,
    min_seen_count: int = DEFAULT_MIN_SEEN_COUNT,
) -> bool:
    """Return whether a reference has enough demand to become a candidate."""

    if not reference.is_active:
        return False
    return reference.selected_count >= min_selected_count or reference.seen_count >= min_seen_count


def queue_external_reference_for_curation(
    reference: ExternalFoodReference,
    *,
    reason: str | None = None,
    priority: int | None = None,
    created_by=None,
) -> CurationCandidateQueueResult:
    """Create or refresh a curator-facing candidate from an external reference.

    The candidate stores provider identifiers and display metadata only. It does
    not copy nutrition payloads, does not create ``CatalogFood`` and does not
    create ``notas.Food``.
    """

    resolved_reason = reason or _infer_reason(reference)
    resolved_priority = _normalize_priority(priority if priority is not None else _infer_priority(reference))
    defaults = {
        "provider": reference.provider,
        "external_food_id": reference.external_food_id,
        "external_serving_id": reference.external_serving_id,
        "display_name": reference.display_name,
        "brand_name": reference.brand_name,
        "source_url": reference.source_url,
        "attribution_text": reference.attribution_text,
        "reason": resolved_reason,
        "priority": resolved_priority,
        "seen_count_at_creation": reference.seen_count,
        "selected_count_at_creation": reference.selected_count,
        "created_by": created_by,
    }
    candidate, created = CatalogCurationCandidate.objects.get_or_create(
        external_reference=reference,
        defaults=defaults,
    )
    if not created:
        updatable_fields = [
            "provider",
            "external_food_id",
            "external_serving_id",
            "display_name",
            "brand_name",
            "source_url",
            "attribution_text",
            "reason",
            "priority",
            "seen_count_at_creation",
            "selected_count_at_creation",
        ]
        for field in updatable_fields:
            setattr(candidate, field, defaults[field])
        if created_by is not None and candidate.created_by_id is None:
            candidate.created_by = created_by
            updatable_fields.append("created_by")
        candidate.save(update_fields=[*updatable_fields, "updated_at"])
    return CurationCandidateQueueResult(candidate=candidate, created=created)


def queue_external_references_for_curation(
    references: Iterable[ExternalFoodReference] | None = None,
    *,
    min_selected_count: int = DEFAULT_MIN_SELECTED_COUNT,
    min_seen_count: int = DEFAULT_MIN_SEEN_COUNT,
    limit: int | None = None,
    created_by=None,
) -> CurationCandidateBulkQueueResult:
    """Queue eligible external references in bulk."""

    if references is None:
        queryset = ExternalFoodReference.objects.filter(is_active=True).order_by(
            "-selected_count",
            "-seen_count",
            "display_name",
        )
        references_iterable: Iterable[ExternalFoodReference] = queryset
    else:
        references_iterable = references

    created_count = 0
    updated_count = 0
    skipped_count = 0
    candidate_ids: list[int] = []

    processed = 0
    for reference in references_iterable:
        if limit is not None and processed >= limit:
            break
        processed += 1
        if not should_queue_external_reference(
            reference,
            min_selected_count=min_selected_count,
            min_seen_count=min_seen_count,
        ):
            skipped_count += 1
            continue
        result = queue_external_reference_for_curation(reference, created_by=created_by)
        candidate_ids.append(result.candidate.pk)
        if result.created:
            created_count += 1
        else:
            updated_count += 1

    return CurationCandidateBulkQueueResult(
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        candidate_ids=tuple(candidate_ids),
    )


def _infer_reason(reference: ExternalFoodReference) -> str:
    if reference.selected_count >= DEFAULT_MIN_SELECTED_COUNT:
        return CatalogCurationCandidate.REASON_EXTERNAL_SELECTED
    return CatalogCurationCandidate.REASON_EXTERNAL_DEMAND


def _infer_priority(reference: ExternalFoodReference) -> int:
    if reference.selected_count >= DEFAULT_MIN_SELECTED_COUNT:
        return min(100, DEFAULT_SELECTED_PRIORITY + min(reference.selected_count, 20))
    return min(100, DEFAULT_DEMAND_PRIORITY + min(reference.seen_count, 20))


def _normalize_priority(value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 50
    return max(0, min(100, parsed))


__all__ = [
    "DEFAULT_MIN_SEEN_COUNT",
    "DEFAULT_MIN_SELECTED_COUNT",
    "CurationCandidateBulkQueueResult",
    "CurationCandidateQueueResult",
    "queue_external_reference_for_curation",
    "queue_external_references_for_curation",
    "should_queue_external_reference",
]
