"""Governed preparation of USDA rows selected by the coverage manifest."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from food_catalog.application.coverage_manifest import CoverageManifest, load_coverage_manifest
from food_catalog.application.imports.usda.foundation_foods_reader import (
    read_foundation_food_payloads_from_json,
)
from food_catalog.application.imports.usda.manifest_selection import (
    USDAManifestSelection,
    select_usda_manifest_foods,
)
from food_catalog.infrastructure.imports.catalog_import import CATALOG_SOURCE_NAME_USDA
from food_catalog.infrastructure.imports.governance import CatalogImportIdentity, catalog_import_identity
from food_catalog.models import CatalogFood


@dataclass(frozen=True)
class PreparedUSDAManifestImport:
    manifest: CoverageManifest
    selection: USDAManifestSelection
    identity: CatalogImportIdentity


def prepare_usda_manifest_import(
    *,
    dataset_path: str | Path,
    manifest_path: str | Path,
    manifest_version: str,
    expected_source: str,
    offset: int,
    limit: int,
    source_name: str = CATALOG_SOURCE_NAME_USDA,
) -> PreparedUSDAManifestImport:
    dataset_path = Path(dataset_path)
    manifest = load_coverage_manifest(manifest_path, version=manifest_version)
    payloads = read_foundation_food_payloads_from_json(dataset_path)
    selection = select_usda_manifest_foods(
        manifest=manifest,
        payloads=payloads,
        expected_source=expected_source,
        offset=offset,
        limit=limit,
    )
    if not selection.targets:
        raise ValueError("The manifest contains no mapped targets for this USDA source.")
    source_versions = {target.source_version for target in selection.targets}
    source_datasets = {target.source_dataset for target in selection.targets}
    if len(source_versions) != 1 or len(source_datasets) != 1:
        raise ValueError("A governed USDA wave must use one dataset and one source version.")

    identity = catalog_import_identity(
        source_type=CatalogFood.SOURCE_USDA,
        source_name=source_name,
        source_version=next(iter(source_versions)),
        input_sha256=hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        parameters_payload={
            "manifest_version": manifest.version,
            "manifest_sha256": manifest.sha256,
            "expected_source": expected_source,
            "source_dataset": next(iter(source_datasets)),
            "limit": limit,
            "offset": offset,
            "target_keys": [target.target_key for target in selection.targets],
        },
    )
    return PreparedUSDAManifestImport(manifest=manifest, selection=selection, identity=identity)


__all__ = ["PreparedUSDAManifestImport", "prepare_usda_manifest_import"]
