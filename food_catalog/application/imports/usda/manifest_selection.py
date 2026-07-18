"""Select only explicitly mapped USDA rows from a coverage manifest."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from food_catalog.application.coverage_manifest import CoverageManifest, CoverageTarget
from food_catalog.application.imports.contracts import ImportedFoodDTO
from food_catalog.application.imports.usda.mapper import map_usda_food_to_imported_food_dto


class USDAManifestSelectionError(ValueError):
    """Raised when a mapped target cannot be reconciled with its USDA dataset."""


@dataclass(frozen=True)
class USDAManifestSelection:
    targets: tuple[CoverageTarget, ...]
    foods: tuple[ImportedFoodDTO, ...]


def select_usda_manifest_foods(
    *,
    manifest: CoverageManifest,
    payloads: Iterable[dict],
    expected_source: str,
    offset: int = 0,
    limit: int | None = None,
) -> USDAManifestSelection:
    """Map source-controlled FDC IDs to official payloads without persistence."""

    if expected_source not in {"usda_foundation", "usda_sr_legacy"}:
        raise USDAManifestSelectionError(f"Unsupported USDA manifest source: {expected_source}")
    if limit is not None and limit < 1:
        raise USDAManifestSelectionError("Selection limit must be positive.")
    if offset < 0:
        raise USDAManifestSelectionError("Selection offset cannot be negative.")

    mapped_targets = [
        target
        for target in manifest.targets
        if target.expected_source == expected_source and target.mapping_status == "mapped"
    ]
    mapped_targets = mapped_targets[offset:]
    if limit is not None:
        mapped_targets = mapped_targets[:limit]

    payload_by_id: dict[str, dict] = {}
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        source_food_id = str(payload.get("fdcId", "")).strip()
        if source_food_id:
            payload_by_id[source_food_id] = payload

    missing = [target.source_food_id for target in mapped_targets if target.source_food_id not in payload_by_id]
    if missing:
        raise USDAManifestSelectionError(
            "Mapped FDC IDs are absent from the supplied dataset: " + ", ".join(missing)
        )

    foods = tuple(
        map_usda_food_to_imported_food_dto(
            payload_by_id[target.source_food_id],
            source_version=target.source_version,
            source_dataset=target.source_dataset,
            preferred_name=target.preferred_name_es,
            food_subgroup=target.subcategory,
            preparation_state=target.preparation_state,
        )
        for target in mapped_targets
    )
    return USDAManifestSelection(targets=tuple(mapped_targets), foods=foods)


__all__ = [
    "USDAManifestSelection",
    "USDAManifestSelectionError",
    "select_usda_manifest_foods",
]
