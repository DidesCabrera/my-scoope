"""External food reference helpers.

External provider responses are lookup data, not Food Catalog master data. This
module stores only references, attribution and payload hashes so the product can
remember what was selected while still re-fetching provider-owned nutrition data
according to provider terms.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping

from food_catalog.application.external_providers.contracts import (
    ExternalFoodDetail,
    ExternalFoodSearchResult,
    ExternalFoodServing,
)
from food_catalog.models import ExternalFoodReference, ExternalProviderFetchLog

EXTERNAL_REFERENCE_REFRESH_HOURS = 24


@dataclass(frozen=True)
class ExternalFoodReferenceResult:
    """Result of recording an external food reference."""

    reference: ExternalFoodReference
    created: bool


def external_reference_expires_at(*, now: datetime | None = None) -> datetime:
    """Return the default refresh deadline for provider-owned lookup data."""

    timestamp = now or datetime.now(UTC)
    return timestamp + timedelta(hours=EXTERNAL_REFERENCE_REFRESH_HOURS)


def hash_external_payload(payload: Mapping[str, Any] | None) -> str:
    """Return a stable SHA-256 hash for a provider payload without storing it."""

    if not payload:
        return ""
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def upsert_external_food_reference_from_search_result(
    result: ExternalFoodSearchResult,
    *,
    now: datetime | None = None,
) -> ExternalFoodReferenceResult:
    """Record that an external search result was seen.

    This does not create ``CatalogFood`` and does not create ``notas.Food``.
    """

    timestamp = now or datetime.now(UTC)
    defaults = {
        "display_name": result.name,
        "brand_name": result.brand_name,
        "source_url": result.source_url,
        "attribution_text": result.attribution_text,
        "raw_payload_hash": hash_external_payload(result.raw_payload),
        "last_fetched_at": timestamp,
        "expires_at": external_reference_expires_at(now=timestamp),
        "is_active": True,
    }
    reference, created = ExternalFoodReference.objects.get_or_create(
        provider=result.provider,
        external_food_id=result.external_food_id,
        external_serving_id="",
        defaults={**defaults, "seen_count": 1},
    )
    if not created:
        for field, value in defaults.items():
            setattr(reference, field, value)
        reference.seen_count += 1
        reference.save(
            update_fields=[
                *defaults.keys(),
                "seen_count",
                "last_seen_at",
            ]
        )
    return ExternalFoodReferenceResult(reference=reference, created=created)


def upsert_external_food_reference_from_detail(
    detail: ExternalFoodDetail,
    *,
    serving: ExternalFoodServing | None = None,
    selected: bool = False,
    now: datetime | None = None,
) -> ExternalFoodReferenceResult:
    """Record an external food/detail or serving reference.

    If ``selected`` is true, ``selected_count`` is incremented. Nutrition values
    carried by the provider DTO are not persisted here; only hashes and provider
    identifiers are stored.
    """

    timestamp = now or datetime.now(UTC)
    serving_id = serving.external_serving_id if serving is not None else ""
    payload_hash = hash_external_payload(serving.raw_payload if serving is not None else detail.raw_payload)
    defaults = {
        "display_name": detail.name,
        "brand_name": detail.brand_name,
        "source_url": detail.source_url,
        "attribution_text": detail.attribution_text,
        "raw_payload_hash": payload_hash,
        "detail_payload_hash": hash_external_payload(detail.raw_payload),
        "last_fetched_at": timestamp,
        "expires_at": external_reference_expires_at(now=timestamp),
        "is_active": True,
    }
    reference, created = ExternalFoodReference.objects.get_or_create(
        provider=detail.provider,
        external_food_id=detail.external_food_id,
        external_serving_id=serving_id,
        defaults={**defaults, "seen_count": 1, "selected_count": 1 if selected else 0},
    )
    if not created:
        for field, value in defaults.items():
            setattr(reference, field, value)
        reference.seen_count += 1
        if selected:
            reference.selected_count += 1
        reference.save(
            update_fields=[
                *defaults.keys(),
                "seen_count",
                "selected_count",
                "last_seen_at",
            ]
        )
    return ExternalFoodReferenceResult(reference=reference, created=created)


def record_external_provider_fetch(
    *,
    provider: str,
    lookup_type: str,
    status: str,
    query: str = "",
    external_food_id: str = "",
    external_serving_id: str = "",
    status_code: int | None = None,
    error_message: str = "",
    raw_payload: Mapping[str, Any] | None = None,
    expires_at: datetime | None = None,
) -> ExternalProviderFetchLog:
    """Create a fetch log entry without storing provider response bodies."""

    return ExternalProviderFetchLog.objects.create(
        provider=provider,
        lookup_type=lookup_type,
        status=status,
        query=query.strip(),
        external_food_id=external_food_id.strip(),
        external_serving_id=external_serving_id.strip(),
        status_code=status_code,
        error_message=error_message.strip(),
        raw_payload_hash=hash_external_payload(raw_payload),
        expires_at=expires_at,
    )


__all__ = [
    "EXTERNAL_REFERENCE_REFRESH_HOURS",
    "ExternalFoodReferenceResult",
    "external_reference_expires_at",
    "hash_external_payload",
    "record_external_provider_fetch",
    "upsert_external_food_reference_from_detail",
    "upsert_external_food_reference_from_search_result",
]
