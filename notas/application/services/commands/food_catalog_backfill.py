"""Backfill trusted operational foods into the master Food Catalog.

This bridge runs in ``notas`` because it reads ``notas.Food``. It writes
``food_catalog`` master candidates, but it does not make Food Catalog an
operational nutrition source and it does not expose any catalog data to MCP.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable
import hashlib

from django.db import IntegrityError, transaction
from django.utils import timezone

from food_catalog.models import (
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
    CatalogImportBatch,
)
from food_catalog.infrastructure.imports.governance import (
    catalog_import_identity,
    start_catalog_import_batch,
)
from notas.domain.models import Food, FoodAlias, FoodLocalizedName, FoodSourceMetadata


OPERATIONAL_BACKFILL_SOURCE_NAME = "My Scoope operational foods"
OPERATIONAL_BACKFILL_SOURCE_DATASET = "notas.Food"
DEFAULT_OPERATIONAL_BACKFILL_SOURCE_VERSION = "operational-backfill-v1"
DEFAULT_OPERATIONAL_BACKFILL_STATUS = CatalogFood.STATUS_PENDING_REVIEW


@dataclass(frozen=True)
class OperationalFoodBackfillSample:
    food_id: int
    name: str
    reason: str


@dataclass(frozen=True)
class OperationalFoodCatalogBackfillResult:
    """Summary of an operational ``notas.Food`` -> ``CatalogFood`` backfill."""

    batch: CatalogImportBatch | None
    total_rows: int
    created_rows: int
    skipped_rows: int
    failed_rows: int
    dry_run: bool
    reason_counts: dict[str, int] = field(default_factory=dict)
    samples: dict[str, list[OperationalFoodBackfillSample]] = field(default_factory=dict)
    created_catalog_food_ids: tuple[int, ...] = ()


class OperationalFoodCatalogBackfillError(ValueError):
    """Raised when a backfill cannot be planned or executed."""


def dry_run_backfill_catalog_from_operational_foods(
    *,
    limit: int | None = None,
    source_name: str = OPERATIONAL_BACKFILL_SOURCE_NAME,
    source_version: str = DEFAULT_OPERATIONAL_BACKFILL_SOURCE_VERSION,
    status: str = DEFAULT_OPERATIONAL_BACKFILL_STATUS,
    sample_size: int = 0,
) -> OperationalFoodCatalogBackfillResult:
    """Plan a backfill without writing any ``food_catalog`` rows."""

    return backfill_catalog_from_operational_foods(
        dry_run=True,
        limit=limit,
        source_name=source_name,
        source_version=source_version,
        status=status,
        sample_size=sample_size,
    )


def backfill_catalog_from_operational_foods(
    *,
    dry_run: bool = False,
    limit: int | None = None,
    source_name: str = OPERATIONAL_BACKFILL_SOURCE_NAME,
    source_version: str = DEFAULT_OPERATIONAL_BACKFILL_SOURCE_VERSION,
    status: str = DEFAULT_OPERATIONAL_BACKFILL_STATUS,
    notes: str = "",
    sample_size: int = 0,
    dry_run_batch: CatalogImportBatch | None = None,
    requested_by=None,
    reason: str = "",
) -> OperationalFoodCatalogBackfillResult:
    """Create master catalog candidates from trusted operational foods.

    Eligibility is intentionally conservative: only active, verified, global
    ``notas.Food`` rows are considered. The command does not update the source
    ``Food`` rows, does not publish catalog records, and does not change MCP
    availability.
    """

    _validate_status(status)

    foods = list(_trusted_operational_foods(limit=limit))
    reason_counts: Counter[str] = Counter()
    samples: dict[str, list[OperationalFoodBackfillSample]] = {}
    created_catalog_food_ids: list[int] = []

    existing_source_food_ids = _existing_source_food_ids(
        source_name=source_name,
        foods=foods,
    )
    existing_canonical_names = _existing_catalog_canonical_names(foods=foods)
    seen_canonical_names: set[str] = set()

    batch = None
    if not dry_run:
        if dry_run_batch is None:
            raise OperationalFoodCatalogBackfillError("A governed dry-run batch is required.")
        batch = start_catalog_import_batch(
            identity=operational_backfill_identity(
                source_name=source_name,
                source_version=source_version,
                limit=limit,
                status=status,
            ),
            dry_run_batch=dry_run_batch,
            total_rows=len(foods),
            requested_by=requested_by,
            reason=reason,
            notes=notes,
        )

    created_rows = 0
    skipped_rows = 0
    failed_rows = 0

    for food in foods:
        reason = _skip_reason(
            food=food,
            source_food_ids_seen=existing_source_food_ids,
            catalog_canonical_names_seen=existing_canonical_names,
            selected_canonical_names_seen=seen_canonical_names,
        )

        canonical_name = _canonical_name_for_food(food)
        if reason:
            skipped_rows += 1
            reason_counts[reason] += 1
            _append_sample(
                samples=samples,
                sample_size=sample_size,
                reason=reason,
                food=food,
            )
            if canonical_name:
                seen_canonical_names.add(canonical_name)
            continue

        seen_canonical_names.add(canonical_name)

        if dry_run:
            created_rows += 1
            reason_counts["would_create"] += 1
            continue

        try:
            catalog_food = _create_catalog_food_from_operational_food(
                food=food,
                batch=batch,
                source_name=source_name,
                source_version=source_version,
                status=status,
            )
            created_rows += 1
            created_catalog_food_ids.append(catalog_food.id)
            existing_source_food_ids.add(str(food.id))
            existing_canonical_names.add(catalog_food.canonical_name)
        except IntegrityError:
            failed_rows += 1
            reason_counts["integrity_error"] += 1
            _append_sample(
                samples=samples,
                sample_size=sample_size,
                reason="integrity_error",
                food=food,
            )

    if batch is not None:
        batch.imported_rows = created_rows
        batch.skipped_rows = skipped_rows
        batch.failed_rows = failed_rows
        batch.status = (
            CatalogImportBatch.STATUS_COMPLETED_WITH_ERRORS
            if failed_rows
            else CatalogImportBatch.STATUS_COMPLETED
        )
        batch.finished_at = timezone.now()
        batch.summary_payload = {
            "reason_counts": dict(reason_counts),
            "created_catalog_food_ids": created_catalog_food_ids,
            "dry_run": False,
        }
        batch.save(
            update_fields=[
                "imported_rows",
                "skipped_rows",
                "failed_rows",
                "status",
                "finished_at",
                "summary_payload",
            ]
        )

    return OperationalFoodCatalogBackfillResult(
        batch=batch,
        total_rows=len(foods),
        created_rows=created_rows,
        skipped_rows=skipped_rows,
        failed_rows=failed_rows,
        dry_run=dry_run,
        reason_counts=dict(reason_counts),
        samples=samples,
        created_catalog_food_ids=tuple(created_catalog_food_ids),
    )


def operational_backfill_identity(*, source_name: str, source_version: str, limit: int | None, status: str):
    selection_contract = "notas.Food:is_global=true,is_verified=true,is_active=true:order=id:v1"
    return catalog_import_identity(
        source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        source_name=source_name,
        source_version=source_version,
        input_sha256=hashlib.sha256(selection_contract.encode()).hexdigest(),
        parameters_payload={"limit": limit, "status": status, "selection_contract": selection_contract},
    )


def _trusted_operational_foods(*, limit: int | None) -> Iterable[Food]:
    queryset = (
        Food.objects
        .filter(is_global=True, is_verified=True, is_active=True)
        .select_related("source_metadata")
        .prefetch_related("portions", "aliases", "localized_names")
        .order_by("id")
    )

    if limit is not None:
        if limit < 0:
            raise OperationalFoodCatalogBackfillError("limit must be greater than or equal to 0.")
        queryset = queryset[:limit]

    return queryset


def _validate_status(status: str) -> None:
    allowed_statuses = {
        CatalogFood.STATUS_MANUAL_CANDIDATE,
        CatalogFood.STATUS_NORMALIZED,
        CatalogFood.STATUS_PENDING_REVIEW,
        CatalogFood.STATUS_REVIEWED,
        CatalogFood.STATUS_VERIFIED,
    }
    if status not in allowed_statuses:
        raise OperationalFoodCatalogBackfillError(
            "Backfill status must be a non-published curation status."
        )


def _existing_source_food_ids(*, source_name: str, foods: list[Food]) -> set[str]:
    source_food_ids = [str(food.id) for food in foods]
    if not source_food_ids:
        return set()

    return set(
        CatalogFoodSource.objects.filter(
            source_name=source_name,
            source_food_id__in=source_food_ids,
        ).values_list("source_food_id", flat=True)
    )


def _existing_catalog_canonical_names(*, foods: list[Food]) -> set[str]:
    canonical_names = [_canonical_name_for_food(food) for food in foods]
    canonical_names = [name for name in canonical_names if name]
    if not canonical_names:
        return set()

    return set(
        CatalogFood.objects.filter(
            canonical_name__in=canonical_names,
            brand_name="",
            country="",
        ).values_list("canonical_name", flat=True)
    )


def _skip_reason(
    *,
    food: Food,
    source_food_ids_seen: set[str],
    catalog_canonical_names_seen: set[str],
    selected_canonical_names_seen: set[str],
) -> str:
    if food.catalog_food_id is not None or food.catalog_food_ref is not None:
        return "already_linked_to_catalog"

    if not food.name.strip():
        return "invalid_missing_name"

    if food.protein < 0:
        return "invalid_negative_protein"
    if food.carbs < 0:
        return "invalid_negative_carbs"
    if food.fat < 0:
        return "invalid_negative_fat"
    if food.protein + food.carbs + food.fat > 100:
        return "invalid_total_macros_over_limit"

    if str(food.id) in source_food_ids_seen:
        return "already_backfilled_source_id"

    canonical_name = _canonical_name_for_food(food)
    if not canonical_name:
        return "invalid_missing_canonical_name"

    if canonical_name in catalog_canonical_names_seen:
        return "already_cataloged_canonical_name"

    if canonical_name in selected_canonical_names_seen:
        return "duplicate_canonical_in_selection"

    return ""


@transaction.atomic
def _create_catalog_food_from_operational_food(
    *,
    food: Food,
    batch: CatalogImportBatch | None,
    source_name: str,
    source_version: str,
    status: str,
) -> CatalogFood:
    catalog_food = CatalogFood.objects.create(
        display_name=food.name.strip(),
        canonical_name=_canonical_name_for_food(food),
        protein_g_per_100g=_decimal_3(food.protein),
        carbs_g_per_100g=_decimal_3(food.carbs),
        fat_g_per_100g=_decimal_3(food.fat),
        calories_kcal_per_100g=_decimal_3(food.total_kcal),
        fiber_g_per_100g=_optional_decimal_3(food.fiber_g_per_100g),
        sugar_g_per_100g=_optional_decimal_3(food.sugar_g_per_100g),
        saturated_fat_g_per_100g=_optional_decimal_3(food.saturated_fat_g_per_100g),
        sodium_mg_per_100g=_optional_decimal_3(food.sodium_mg_per_100g),
        food_group=food.food_group,
        food_subgroup=food.food_subgroup,
        status=status,
        source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        data_quality_score=food.data_quality_score,
    )

    _create_catalog_source_from_operational_food(
        catalog_food=catalog_food,
        food=food,
        batch=batch,
        source_name=source_name,
        source_version=source_version,
    )
    _copy_operational_food_portions(catalog_food=catalog_food, food=food)
    _copy_operational_food_aliases(catalog_food=catalog_food, food=food)

    return catalog_food


def _create_catalog_source_from_operational_food(
    *,
    catalog_food: CatalogFood,
    food: Food,
    batch: CatalogImportBatch | None,
    source_name: str,
    source_version: str,
) -> CatalogFoodSource:
    source_metadata = _source_metadata_for_food(food)

    return CatalogFoodSource.objects.create(
        catalog_food=catalog_food,
        import_batch=batch,
        source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        source_name=source_name,
        source_food_id=str(food.id),
        source_dataset=OPERATIONAL_BACKFILL_SOURCE_DATASET,
        source_version=source_version,
        source_url=source_metadata.source_url if source_metadata else "",
        raw_payload_hash=source_metadata.raw_payload_hash if source_metadata else "",
        normalized_payload_hash=source_metadata.normalized_payload_hash if source_metadata else "",
        license_name=source_metadata.license_name if source_metadata else "",
        license_status=_license_status_for_source_metadata(source_metadata),
        attribution=source_metadata.attribution if source_metadata else "My Scoope operational food backfill",
        evidence_payload=_evidence_payload_for_food(food=food, source_metadata=source_metadata),
    )


def _copy_operational_food_portions(*, catalog_food: CatalogFood, food: Food) -> int:
    seen_labels: set[str] = set()
    created_count = 0

    for portion in food.portions.all().order_by("-is_default", "label", "id"):
        label = portion.label.strip()
        if not label:
            continue
        normalized_label = _normalize_text(label)
        if normalized_label in seen_labels:
            continue
        seen_labels.add(normalized_label)

        CatalogFoodPortion.objects.create(
            catalog_food=catalog_food,
            label=label,
            grams=portion.grams,
            source=portion.source or OPERATIONAL_BACKFILL_SOURCE_NAME,
            is_default=portion.is_default,
        )
        created_count += 1

    return created_count


def _copy_operational_food_aliases(*, catalog_food: CatalogFood, food: Food) -> int:
    seen_keys: set[tuple[str, str, str]] = set()
    created_count = 0

    for alias in food.aliases.all().order_by("name", "id"):
        if _create_catalog_alias_if_needed(
            catalog_food=catalog_food,
            name=alias.name,
            normalized_name=alias.normalized_name,
            language=alias.language,
            country=alias.country,
            alias_type=CatalogFoodAlias.ALIAS_COMMON,
            is_primary=False,
            seen_keys=seen_keys,
        ):
            created_count += 1

    for localized_name in food.localized_names.all().order_by("-is_primary", "name", "id"):
        if _create_catalog_alias_if_needed(
            catalog_food=catalog_food,
            name=localized_name.name,
            normalized_name=localized_name.normalized_name,
            language=localized_name.language,
            country=localized_name.country,
            alias_type=CatalogFoodAlias.ALIAS_LOCALIZED,
            is_primary=localized_name.is_primary,
            seen_keys=seen_keys,
        ):
            created_count += 1

    return created_count


def _create_catalog_alias_if_needed(
    *,
    catalog_food: CatalogFood,
    name: str,
    normalized_name: str,
    language: str,
    country: str,
    alias_type: str,
    is_primary: bool,
    seen_keys: set[tuple[str, str, str]],
) -> bool:
    clean_name = name.strip()
    if not clean_name:
        return False

    clean_normalized_name = normalized_name.strip() or _normalize_text(clean_name)
    key = (clean_normalized_name, language, country)
    if key in seen_keys:
        return False

    seen_keys.add(key)
    CatalogFoodAlias.objects.create(
        catalog_food=catalog_food,
        name=clean_name,
        normalized_name=clean_normalized_name,
        alias_type=alias_type,
        language=language,
        country=country,
        is_primary=is_primary,
    )
    return True


def _source_metadata_for_food(food: Food) -> FoodSourceMetadata | None:
    try:
        return food.source_metadata
    except FoodSourceMetadata.DoesNotExist:
        return None


def _license_status_for_source_metadata(
    source_metadata: FoodSourceMetadata | None,
) -> str:
    if source_metadata is None:
        return CatalogFoodSource.LICENSE_UNKNOWN

    license_name = source_metadata.license_name.strip().lower()
    if license_name in {"cc0", "public domain"}:
        return CatalogFoodSource.LICENSE_ALLOWED
    if license_name:
        return CatalogFoodSource.LICENSE_NEEDS_REVIEW
    return CatalogFoodSource.LICENSE_UNKNOWN


def _evidence_payload_for_food(
    *,
    food: Food,
    source_metadata: FoodSourceMetadata | None,
) -> dict:
    payload = {
        "source": "notas.Food",
        "operational_food_id": food.id,
        "name": food.name,
        "canonical_name": _canonical_name_for_food(food),
        "is_global": food.is_global,
        "is_verified": food.is_verified,
        "is_active": food.is_active,
        "visibility": food.visibility,
        "data_quality_score": food.data_quality_score,
        "nutrients_per_100g": {
            "protein_g": str(_decimal_3(food.protein)),
            "carbs_g": str(_decimal_3(food.carbs)),
            "fat_g": str(_decimal_3(food.fat)),
            "calories_kcal": str(_decimal_3(food.total_kcal)),
            "fiber_g": _optional_decimal_as_string(food.fiber_g_per_100g),
            "sugar_g": _optional_decimal_as_string(food.sugar_g_per_100g),
            "saturated_fat_g": _optional_decimal_as_string(food.saturated_fat_g_per_100g),
            "sodium_mg": _optional_decimal_as_string(food.sodium_mg_per_100g),
        },
    }

    if source_metadata is not None:
        payload["original_source_metadata"] = {
            "source": source_metadata.source,
            "source_food_id": source_metadata.source_food_id,
            "source_dataset": source_metadata.source_dataset,
            "source_version": source_metadata.source_version,
            "source_url": source_metadata.source_url,
            "raw_payload_hash": source_metadata.raw_payload_hash,
            "normalized_payload_hash": source_metadata.normalized_payload_hash,
            "license_name": source_metadata.license_name,
            "attribution": source_metadata.attribution,
        }

    return payload


def _canonical_name_for_food(food: Food) -> str:
    return _normalize_text(food.canonical_name or food.name)


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _decimal_3(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def _optional_decimal_3(value) -> Decimal | None:
    if value is None:
        return None
    return _decimal_3(value)


def _optional_decimal_as_string(value) -> str | None:
    decimal_value = _optional_decimal_3(value)
    if decimal_value is None:
        return None
    return str(decimal_value)


def _append_sample(
    *,
    samples: dict[str, list[OperationalFoodBackfillSample]],
    sample_size: int,
    reason: str,
    food: Food,
) -> None:
    if sample_size <= 0:
        return

    reason_samples = samples.setdefault(reason, [])
    if len(reason_samples) >= sample_size:
        return

    reason_samples.append(
        OperationalFoodBackfillSample(
            food_id=food.id,
            name=food.name,
            reason=reason,
        )
    )


__all__ = [
    "DEFAULT_OPERATIONAL_BACKFILL_SOURCE_VERSION",
    "DEFAULT_OPERATIONAL_BACKFILL_STATUS",
    "OPERATIONAL_BACKFILL_SOURCE_DATASET",
    "OPERATIONAL_BACKFILL_SOURCE_NAME",
    "OperationalFoodBackfillSample",
    "OperationalFoodCatalogBackfillError",
    "OperationalFoodCatalogBackfillResult",
    "backfill_catalog_from_operational_foods",
    "dry_run_backfill_catalog_from_operational_foods",
]
