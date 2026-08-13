"""One-time, resumable evidence backfill for historical USDA imports."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from food_catalog.models import CatalogFoodSource

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "usda_sr_legacy_portions_v1.json"
BACKFILL_VERSION = "usda-sr-legacy-portions.v1"


@dataclass(frozen=True)
class SourcePortionBackfillResult:
    batch_ref: str
    proposed: int
    applied: int
    remaining: int
    next_after_id: int | None
    rows: tuple[dict, ...]


def source_portion_backfill_candidates(*, food_ids=None, after_id: int = 0):
    evidence = load_portion_evidence()
    queryset = CatalogFoodSource.objects.filter(
        source_type="usda",
        license_status=CatalogFoodSource.LICENSE_ALLOWED,
        source_food_id__in=evidence["portions"],
        id__gt=after_id,
    ).select_related("catalog_food").order_by("id")
    if food_ids:
        queryset = queryset.filter(catalog_food_id__in=food_ids)
    return [source for source in queryset if not (source.evidence_payload or {}).get("source_portions")]


def backfill_source_portions(
    *, food_ids=None, after_id: int = 0, limit: int = 10, apply: bool = False, reason: str = ""
) -> SourcePortionBackfillResult:
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")
    if apply and not reason.strip():
        raise ValueError("reason is required when applying a backfill")

    evidence = load_portion_evidence()
    candidates = source_portion_backfill_candidates(food_ids=food_ids, after_id=after_id)
    selected = candidates[:limit]
    batch_ref = str(uuid.uuid4())
    rows = tuple({
        "source_id": source.pk,
        "catalog_food_id": source.catalog_food_id,
        "display_name": source.catalog_food.display_name,
        "source_food_id": source.source_food_id,
        "source_portions": evidence["portions"][source.source_food_id],
    } for source in selected)

    if apply:
        _apply_rows(rows, evidence=evidence, batch_ref=batch_ref, reason=reason)

    remaining = max(0, len(candidates) - len(selected))
    return SourcePortionBackfillResult(
        batch_ref=batch_ref,
        proposed=len(rows),
        applied=len(rows) if apply else 0,
        remaining=remaining,
        next_after_id=selected[-1].pk if remaining and selected else None,
        rows=rows,
    )


@transaction.atomic
def _apply_rows(rows, *, evidence, batch_ref: str, reason: str):
    locked = {
        source.pk: source
        for source in CatalogFoodSource.objects.select_for_update().filter(pk__in=[row["source_id"] for row in rows])
    }
    applied_at = timezone.now()
    for row in rows:
        source = locked[row["source_id"]]
        payload = dict(source.evidence_payload or {})
        if payload.get("source_portions"):
            continue
        payload["source_portions"] = row["source_portions"]
        payload["source_portions_provenance"] = {
            "batch_ref": batch_ref,
            "backfill_version": BACKFILL_VERSION,
            "dataset": evidence["dataset"],
            "dataset_version": evidence["version"],
            "evidence_url": evidence["evidence_url_template"].format(fdc_id=source.source_food_id),
            "reason": reason.strip(),
            "applied_at": applied_at.isoformat(),
        }
        source.evidence_payload = payload
        source.last_checked_at = applied_at
        source.save(update_fields=["evidence_payload", "last_checked_at"])


def load_portion_evidence():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


__all__ = [
    "BACKFILL_VERSION",
    "SourcePortionBackfillResult",
    "backfill_source_portions",
    "load_portion_evidence",
    "source_portion_backfill_candidates",
]
