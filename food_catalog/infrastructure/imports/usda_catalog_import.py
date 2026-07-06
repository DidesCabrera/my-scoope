"""USDA-specific orchestration for Food Catalog master imports."""

from __future__ import annotations

from typing import Iterable

from food_catalog.application.imports.usda.mapper import (
    USDA_SOURCE_DATASET_DEFAULT,
    map_usda_food_to_imported_food_dto,
)
from food_catalog.infrastructure.imports.catalog_import import (
    CATALOG_SOURCE_NAME_USDA,
    CatalogImportResult,
    DryRunCatalogImportResult,
    dry_run_catalog_food_import,
    import_catalog_food_batch,
)


def dry_run_usda_catalog_food_payloads(
    *,
    payloads: Iterable[dict],
    source_version: str,
    source_dataset: str = USDA_SOURCE_DATASET_DEFAULT,
    source_name: str = CATALOG_SOURCE_NAME_USDA,
    sample_size: int = 0,
) -> DryRunCatalogImportResult:
    dtos = [
        map_usda_food_to_imported_food_dto(
            payload,
            source_version=source_version,
            source_dataset=source_dataset,
        )
        for payload in payloads
    ]

    return dry_run_catalog_food_import(
        foods=dtos,
        source_name=source_name,
        sample_size=sample_size,
    )


def import_usda_catalog_food_payloads(
    *,
    payloads: Iterable[dict],
    source_version: str,
    source_dataset: str = USDA_SOURCE_DATASET_DEFAULT,
    source_name: str = CATALOG_SOURCE_NAME_USDA,
    notes: str = "",
) -> CatalogImportResult:
    dtos = [
        map_usda_food_to_imported_food_dto(
            payload,
            source_version=source_version,
            source_dataset=source_dataset,
        )
        for payload in payloads
    ]

    return import_catalog_food_batch(
        foods=dtos,
        source_name=source_name,
        source_version=source_version,
        notes=notes,
    )
