"""Curation workflow helpers for master Food Catalog records.

The model already exposes rich status values. This module makes those values
behave like an explicit workflow so admin actions and future curator surfaces do
not move records through the catalog lifecycle with blind queryset updates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

from food_catalog.application.publication import check_catalog_food_publishable
from food_catalog.models import CatalogFood

_INITIAL_CANDIDATE_STATUSES = frozenset(
    {
        CatalogFood.STATUS_EXTERNAL_CANDIDATE,
        CatalogFood.STATUS_MANUAL_CANDIDATE,
        CatalogFood.STATUS_BRAND_SUBMITTED,
    }
)

ALLOWED_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    CatalogFood.STATUS_EXTERNAL_CANDIDATE: frozenset(
        {
            CatalogFood.STATUS_NORMALIZED,
            CatalogFood.STATUS_PENDING_REVIEW,
            CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
            CatalogFood.STATUS_REJECTED,
        }
    ),
    CatalogFood.STATUS_MANUAL_CANDIDATE: frozenset(
        {
            CatalogFood.STATUS_NORMALIZED,
            CatalogFood.STATUS_PENDING_REVIEW,
            CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
            CatalogFood.STATUS_REJECTED,
        }
    ),
    CatalogFood.STATUS_BRAND_SUBMITTED: frozenset(
        {
            CatalogFood.STATUS_NORMALIZED,
            CatalogFood.STATUS_PENDING_REVIEW,
            CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
            CatalogFood.STATUS_REJECTED,
        }
    ),
    CatalogFood.STATUS_NORMALIZED: frozenset(
        {
            CatalogFood.STATUS_PENDING_REVIEW,
            CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
            CatalogFood.STATUS_REJECTED,
        }
    ),
    CatalogFood.STATUS_PENDING_REVIEW: frozenset(
        {
            CatalogFood.STATUS_REVIEWED,
            CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
            CatalogFood.STATUS_REJECTED,
        }
    ),
    CatalogFood.STATUS_NEEDS_MORE_EVIDENCE: frozenset(
        {
            CatalogFood.STATUS_NORMALIZED,
            CatalogFood.STATUS_PENDING_REVIEW,
            CatalogFood.STATUS_REJECTED,
            CatalogFood.STATUS_ARCHIVED,
        }
    ),
    CatalogFood.STATUS_REVIEWED: frozenset(
        {
            CatalogFood.STATUS_PENDING_REVIEW,
            CatalogFood.STATUS_VERIFIED,
            CatalogFood.STATUS_PUBLISHED,
            CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
            CatalogFood.STATUS_REJECTED,
            CatalogFood.STATUS_DEPRECATED,
        }
    ),
    CatalogFood.STATUS_VERIFIED: frozenset(
        {
            CatalogFood.STATUS_PUBLISHED,
            CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
            CatalogFood.STATUS_REJECTED,
            CatalogFood.STATUS_DEPRECATED,
        }
    ),
    CatalogFood.STATUS_PUBLISHED: frozenset(
        {
            CatalogFood.STATUS_DEPRECATED,
            CatalogFood.STATUS_ARCHIVED,
        }
    ),
    CatalogFood.STATUS_REJECTED: frozenset(
        {
            CatalogFood.STATUS_PENDING_REVIEW,
            CatalogFood.STATUS_ARCHIVED,
        }
    ),
    CatalogFood.STATUS_DEPRECATED: frozenset({CatalogFood.STATUS_ARCHIVED}),
    CatalogFood.STATUS_ARCHIVED: frozenset(),
}

REVIEW_DECISION_STATUSES = frozenset(
    {
        CatalogFood.STATUS_REVIEWED,
        CatalogFood.STATUS_VERIFIED,
        CatalogFood.STATUS_PUBLISHED,
        CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
        CatalogFood.STATUS_REJECTED,
    }
)


@dataclass(frozen=True)
class CatalogCurationTransitionResult:
    """Result of a single Food Catalog curation transition."""

    changed: bool
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class CatalogCurationBatchResult:
    """Aggregate result for admin/batch curation actions."""

    changed_count: int
    blocked: tuple[str, ...]


def allowed_next_statuses(current_status: str) -> tuple[str, ...]:
    """Return target statuses allowed from ``current_status``."""

    return tuple(sorted(ALLOWED_STATUS_TRANSITIONS.get(current_status, ())))


def can_transition_catalog_food_status(current_status: str, target_status: str) -> bool:
    """Return whether a status transition is allowed by the curation workflow."""

    if current_status == target_status:
        return True
    return target_status in ALLOWED_STATUS_TRANSITIONS.get(current_status, ())


def transition_catalog_food_status(
    catalog_food: CatalogFood,
    target_status: str,
    *,
    user=None,
    now=None,
) -> CatalogCurationTransitionResult:
    """Move a ``CatalogFood`` through the protected curation workflow.

    This function intentionally changes only the master catalog record. It does
    not create or refresh ``notas.Food`` snapshots. Publishing remains only a
    master-catalog decision that makes a record eligible for the explicit
    snapshot protocol.
    """

    if target_status not in dict(CatalogFood.STATUS_CHOICES):
        return CatalogCurationTransitionResult(
            changed=False,
            errors=(f"unknown target status: {target_status}",),
        )

    if catalog_food.status == target_status:
        return CatalogCurationTransitionResult(changed=False)

    if not can_transition_catalog_food_status(catalog_food.status, target_status):
        return CatalogCurationTransitionResult(
            changed=False,
            errors=(
                f"cannot transition from {catalog_food.status} to {target_status}",
            ),
        )

    if target_status == CatalogFood.STATUS_PUBLISHED:
        publication_check = check_catalog_food_publishable(catalog_food)
        if not publication_check.can_publish:
            return CatalogCurationTransitionResult(
                changed=False,
                errors=publication_check.errors,
            )

    timestamp = now or datetime.now(UTC)
    update_fields = ["status"]
    catalog_food.status = target_status

    if target_status in REVIEW_DECISION_STATUSES:
        catalog_food.reviewed_at = timestamp
        update_fields.append("reviewed_at")
        if user is not None and getattr(user, "is_authenticated", False):
            catalog_food.reviewed_by = user
            update_fields.append("reviewed_by")

    if target_status == CatalogFood.STATUS_PUBLISHED:
        catalog_food.published_at = timestamp
        update_fields.append("published_at")

    catalog_food.save(update_fields=update_fields)
    return CatalogCurationTransitionResult(changed=True)


def transition_catalog_foods_status(
    catalog_foods: Iterable[CatalogFood],
    target_status: str,
    *,
    user=None,
) -> CatalogCurationBatchResult:
    """Apply a protected status transition to a batch of catalog foods."""

    changed_count = 0
    blocked: list[str] = []

    for catalog_food in catalog_foods:
        result = transition_catalog_food_status(
            catalog_food,
            target_status,
            user=user,
        )
        if result.changed:
            changed_count += 1
        elif result.errors:
            blocked.append(f"{catalog_food.display_name}: {', '.join(result.errors)}")

    return CatalogCurationBatchResult(
        changed_count=changed_count,
        blocked=tuple(blocked),
    )
