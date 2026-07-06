"""Persistence services for importing candidates into the master Food Catalog.

This module intentionally lives outside ``food_catalog.application`` because it
uses Django models. The pure adapter contracts remain in
``food_catalog.application.imports``.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable

from django.db import IntegrityError, transaction
from django.utils import timezone

from food_catalog.application.imports.contracts import ImportedFoodDTO
from food_catalog.application.imports.normalization import normalize_imported_food
from food_catalog.application.imports.quality import evaluate_imported_food_quality
from food_catalog.models import CatalogFood, CatalogFoodSource, CatalogImportBatch


CATALOG_SOURCE_NAME_USDA = "USDA FoodData Central"
DEFAULT_CATALOG_IMPORT_SOURCE_TYPE = CatalogFood.SOURCE_EXTERNAL_TEMPORARY
DEFAULT_CATALOG_IMPORT_STATUS = CatalogFood.STATUS_EXTERNAL_CANDIDATE


@dataclass(frozen=True)
class CatalogImportIssueSample:
    index: int
    reason: str
    source_food_id: str = ""
    name: str = ""


@dataclass(frozen=True)
class CatalogImportPreparedFood:
    index: int
    dto: ImportedFoodDTO
    quality_score: int


@dataclass(frozen=True)
class DryRunCatalogImportResult:
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    would_import_rows: int
    failed_rows: int
    reason_counts: dict[str, int] = field(default_factory=dict)
    issue_samples: dict[str, list[CatalogImportIssueSample]] = field(default_factory=dict)

    @property
    def skipped_rows(self) -> int:
        return self.invalid_rows + self.duplicate_rows + self.failed_rows


@dataclass(frozen=True)
class CatalogImportResult:
    batch: CatalogImportBatch
    total_rows: int
    imported_rows: int
    skipped_rows: int
    failed_rows: int
    duplicate_rows: int
    invalid_rows: int
    reason_counts: dict[str, int] = field(default_factory=dict)


def dry_run_catalog_food_import(
    *,
    foods: Iterable[ImportedFoodDTO],
    source_name: str,
    source_type: str = DEFAULT_CATALOG_IMPORT_SOURCE_TYPE,
    sample_size: int = 0,
) -> DryRunCatalogImportResult:
    """Validate candidate DTOs without writing catalog rows."""

    food_list = list(foods)
    prepared_foods, invalid_rows, failed_rows, reason_counts, issue_samples = _prepare_foods(
        foods=food_list,
        sample_size=sample_size,
    )

    duplicate_rows = 0
    would_import_rows = 0
    seen_source_ids: set[str] = set()

    source_food_ids = [food.dto.source_food_id for food in prepared_foods if food.dto.source_food_id]
    already_imported_source_ids = set(
        CatalogFoodSource.objects.filter(
            source_name=source_name,
            source_food_id__in=source_food_ids,
        ).values_list("source_food_id", flat=True)
    )

    existing_canonical_names = set(
        CatalogFood.objects.filter(
            canonical_name__in=[food.dto.canonical_name for food in prepared_foods],
            brand_name="",
            country="",
        ).values_list("canonical_name", flat=True)
    )

    for prepared_food in prepared_foods:
        duplicate_reason = _duplicate_reason(
            prepared_food=prepared_food,
            source_food_ids_seen=seen_source_ids,
            already_imported_source_ids=already_imported_source_ids,
            existing_canonical_names=existing_canonical_names,
        )

        if duplicate_reason:
            duplicate_rows += 1
            reason_counts[duplicate_reason] += 1
            _append_issue_sample(
                issue_samples=issue_samples,
                sample_size=sample_size,
                reason=duplicate_reason,
                index=prepared_food.index,
                source_food_id=prepared_food.dto.source_food_id,
                name=prepared_food.dto.name,
            )
            continue

        seen_source_ids.add(prepared_food.dto.source_food_id)
        would_import_rows += 1

    return DryRunCatalogImportResult(
        total_rows=len(food_list),
        valid_rows=len(prepared_foods),
        invalid_rows=invalid_rows,
        duplicate_rows=duplicate_rows,
        would_import_rows=would_import_rows,
        failed_rows=failed_rows,
        reason_counts=dict(reason_counts),
        issue_samples=dict(issue_samples),
    )


@transaction.atomic
def import_catalog_food_batch(
    *,
    foods: Iterable[ImportedFoodDTO],
    source_name: str,
    source_version: str,
    source_type: str = DEFAULT_CATALOG_IMPORT_SOURCE_TYPE,
    notes: str = "",
) -> CatalogImportResult:
    """Persist valid import DTOs as master catalog candidates.

    This command writes ``food_catalog`` models only. It does not create or
    update ``notas.Food``; operational availability still requires the explicit
    snapshot protocol owned by ``notas``.
    """

    food_list = list(foods)
    prepared_foods, invalid_rows, failed_rows, reason_counts, _issue_samples = _prepare_foods(
        foods=food_list,
        sample_size=0,
    )

    batch = CatalogImportBatch.objects.create(
        source_type=source_type,
        source_name=source_name,
        source_version=source_version,
        status=CatalogImportBatch.STATUS_RUNNING,
        total_rows=len(food_list),
        imported_rows=0,
        skipped_rows=0,
        failed_rows=failed_rows,
        notes=notes,
    )

    imported_rows = 0
    duplicate_rows = 0
    seen_source_ids: set[str] = set()

    source_food_ids = [food.dto.source_food_id for food in prepared_foods if food.dto.source_food_id]
    already_imported_source_ids = set(
        CatalogFoodSource.objects.filter(
            source_name=source_name,
            source_food_id__in=source_food_ids,
        ).values_list("source_food_id", flat=True)
    )

    existing_canonical_names = set(
        CatalogFood.objects.filter(
            canonical_name__in=[food.dto.canonical_name for food in prepared_foods],
            brand_name="",
            country="",
        ).values_list("canonical_name", flat=True)
    )

    for prepared_food in prepared_foods:
        duplicate_reason = _duplicate_reason(
            prepared_food=prepared_food,
            source_food_ids_seen=seen_source_ids,
            already_imported_source_ids=already_imported_source_ids,
            existing_canonical_names=existing_canonical_names,
        )

        if duplicate_reason:
            duplicate_rows += 1
            reason_counts[duplicate_reason] += 1
            continue

        seen_source_ids.add(prepared_food.dto.source_food_id)

        try:
            _create_catalog_food_candidate(
                prepared_food=prepared_food,
                batch=batch,
                source_name=source_name,
                source_type=source_type,
            )
            imported_rows += 1
            existing_canonical_names.add(prepared_food.dto.canonical_name)
        except IntegrityError:
            failed_rows += 1
            reason_counts["integrity_error"] += 1

    skipped_rows = invalid_rows + duplicate_rows
    status = (
        CatalogImportBatch.STATUS_COMPLETED_WITH_ERRORS
        if failed_rows
        else CatalogImportBatch.STATUS_COMPLETED
    )

    batch.imported_rows = imported_rows
    batch.skipped_rows = skipped_rows
    batch.failed_rows = failed_rows
    batch.status = status
    batch.finished_at = timezone.now()
    batch.summary_payload = {
        "reason_counts": dict(reason_counts),
        "duplicate_rows": duplicate_rows,
        "invalid_rows": invalid_rows,
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

    return CatalogImportResult(
        batch=batch,
        total_rows=batch.total_rows,
        imported_rows=imported_rows,
        skipped_rows=skipped_rows,
        failed_rows=failed_rows,
        duplicate_rows=duplicate_rows,
        invalid_rows=invalid_rows,
        reason_counts=dict(reason_counts),
    )


def _prepare_foods(
    *,
    foods: list[ImportedFoodDTO],
    sample_size: int,
) -> tuple[
    list[CatalogImportPreparedFood],
    int,
    int,
    Counter[str],
    dict[str, list[CatalogImportIssueSample]],
]:
    prepared_foods: list[CatalogImportPreparedFood] = []
    invalid_rows = 0
    failed_rows = 0
    reason_counts: Counter[str] = Counter()
    issue_samples: dict[str, list[CatalogImportIssueSample]] = defaultdict(list)

    for index, dto in enumerate(foods):
        try:
            normalized_dto = normalize_imported_food(dto)
            quality_result = evaluate_imported_food_quality(normalized_dto)

            if not quality_result.is_valid:
                invalid_rows += 1
                reason = quality_result.reason or "invalid"
                reason_counts[reason] += 1
                _append_issue_sample(
                    issue_samples=issue_samples,
                    sample_size=sample_size,
                    reason=reason,
                    index=index,
                    source_food_id=normalized_dto.source_food_id,
                    name=normalized_dto.name,
                )
                continue

            prepared_foods.append(
                CatalogImportPreparedFood(
                    index=index,
                    dto=normalized_dto,
                    quality_score=quality_result.score,
                )
            )
        except Exception:
            failed_rows += 1
            reason_counts["mapping_failed"] += 1
            _append_issue_sample(
                issue_samples=issue_samples,
                sample_size=sample_size,
                reason="mapping_failed",
                index=index,
            )

    return prepared_foods, invalid_rows, failed_rows, reason_counts, issue_samples


def _duplicate_reason(
    *,
    prepared_food: CatalogImportPreparedFood,
    source_food_ids_seen: set[str],
    already_imported_source_ids: set[str],
    existing_canonical_names: set[str],
) -> str:
    source_food_id = prepared_food.dto.source_food_id

    if source_food_id in source_food_ids_seen:
        return "duplicate_in_file"

    if source_food_id in already_imported_source_ids:
        return "already_imported_source_id"

    if prepared_food.dto.canonical_name in existing_canonical_names:
        return "already_cataloged_canonical_name"

    return ""


def _create_catalog_food_candidate(
    *,
    prepared_food: CatalogImportPreparedFood,
    batch: CatalogImportBatch,
    source_name: str,
    source_type: str,
) -> CatalogFood:
    dto = prepared_food.dto

    with transaction.atomic():
        catalog_food = CatalogFood.objects.create(
            display_name=dto.name,
            canonical_name=dto.canonical_name,
            protein_g_per_100g=dto.protein,
            carbs_g_per_100g=dto.carbs,
            fat_g_per_100g=dto.fat,
            calories_kcal_per_100g=None,
            fiber_g_per_100g=dto.fiber_g_per_100g,
            sugar_g_per_100g=dto.sugar_g_per_100g,
            saturated_fat_g_per_100g=dto.saturated_fat_g_per_100g,
            sodium_mg_per_100g=dto.sodium_mg_per_100g,
            food_group=dto.food_group,
            food_subgroup=dto.food_subgroup,
            status=DEFAULT_CATALOG_IMPORT_STATUS,
            source_type=source_type,
            data_quality_score=prepared_food.quality_score,
        )

        CatalogFoodSource.objects.create(
            catalog_food=catalog_food,
            import_batch=batch,
            source_type=source_type,
            source_name=source_name,
            source_food_id=dto.source_food_id,
            source_dataset=dto.source_dataset,
            source_version=dto.source_version,
            source_url=dto.source_url,
            raw_payload_hash=dto.raw_payload_hash,
            normalized_payload_hash=dto.normalized_payload_hash,
            license_name=dto.license_name,
            license_status=_license_status_for_dto(dto),
            attribution=dto.attribution,
            evidence_payload=_evidence_payload_for_dto(dto),
        )

    return catalog_food


def _license_status_for_dto(dto: ImportedFoodDTO) -> str:
    if dto.license_name.strip().lower() in {"cc0", "public domain"}:
        return CatalogFoodSource.LICENSE_ALLOWED

    if dto.license_name:
        return CatalogFoodSource.LICENSE_NEEDS_REVIEW

    return CatalogFoodSource.LICENSE_UNKNOWN


def _evidence_payload_for_dto(dto: ImportedFoodDTO) -> dict:
    return {
        "source": dto.source,
        "source_food_id": dto.source_food_id,
        "source_dataset": dto.source_dataset,
        "source_version": dto.source_version,
        "name": dto.name,
        "canonical_name": dto.canonical_name,
        "nutrients_per_100g": {
            "protein_g": _decimal_to_string(dto.protein),
            "carbs_g": _decimal_to_string(dto.carbs),
            "fat_g": _decimal_to_string(dto.fat),
            "fiber_g": _decimal_to_string(dto.fiber_g_per_100g),
            "sugar_g": _decimal_to_string(dto.sugar_g_per_100g),
            "saturated_fat_g": _decimal_to_string(dto.saturated_fat_g_per_100g),
            "sodium_mg": _decimal_to_string(dto.sodium_mg_per_100g),
        },
    }


def _decimal_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return str(value)


def _append_issue_sample(
    *,
    issue_samples: dict[str, list[CatalogImportIssueSample]],
    sample_size: int,
    reason: str,
    index: int,
    source_food_id: str = "",
    name: str = "",
) -> None:
    if sample_size <= 0:
        return

    samples = issue_samples[reason]
    if len(samples) >= sample_size:
        return

    samples.append(
        CatalogImportIssueSample(
            index=index,
            reason=reason,
            source_food_id=source_food_id,
            name=name,
        )
    )
