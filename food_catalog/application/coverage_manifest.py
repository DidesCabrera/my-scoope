"""Pure contracts for the versioned generic-food coverage manifest.

Manifest targets are planning records, not catalog foods. Parsing this module never
touches Django or persists data. Real catalog rows still require the governed source
dry-run and apply workflows.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


CATEGORIES = frozenset({"vegetable", "fruit", "meat_seafood", "legume", "dairy"})
PREPARATION_STATES = frozenset({"unknown", "raw", "cooked", "dry", "hydrated", "ready_to_eat"})
PRIORITY_TIERS = frozenset({"A", "B", "C", "discovery"})
CHILE_RELEVANCE_VALUES = frozenset({"essential", "common", "useful", "specialized"})
EXPECTED_SOURCES = frozenset(
    {"unmapped", "internal_seed", "usda_foundation", "usda_sr_legacy", "manual_evidence"}
)
MAPPING_STATUSES = frozenset({"unmapped", "candidate", "mapped", "ambiguous", "blocked"})
COVERAGE_STAGES = (
    "defined",
    "source_mapped",
    "dry_run_valid",
    "imported",
    "reviewed",
    "published",
    "snapshotted",
)
COVERAGE_STATUSES = frozenset((*COVERAGE_STAGES, "deferred", "excluded"))
REQUIRED_COLUMNS = (
    "target_key",
    "preferred_name_es",
    "category",
    "subcategory",
    "preparation_state",
    "priority_tier",
    "chile_relevance",
    "expected_source",
    "source_food_id",
    "source_dataset",
    "source_version",
    "mapping_status",
    "catalog_food_id",
    "coverage_status",
    "discovery_origin",
    "decision_reason",
)

_TARGET_KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CoverageManifestError(ValueError):
    """Raised when a manifest cannot be trusted as a coverage contract."""


@dataclass(frozen=True)
class CoverageTarget:
    target_key: str
    preferred_name_es: str
    category: str
    subcategory: str
    preparation_state: str
    priority_tier: str
    chile_relevance: str
    expected_source: str
    source_food_id: str
    source_dataset: str
    source_version: str
    mapping_status: str
    catalog_food_id: str
    coverage_status: str
    discovery_origin: str
    decision_reason: str

    @property
    def concept_identity(self) -> tuple[str, str, str]:
        return (
            _normalize_name(self.preferred_name_es),
            self.category,
            self.preparation_state,
        )


@dataclass(frozen=True)
class CoverageManifest:
    version: str
    targets: tuple[CoverageTarget, ...]
    sha256: str

    @property
    def total_targets(self) -> int:
        return len(self.targets)

    def counts_by_category(self) -> dict[str, int]:
        return dict(sorted(Counter(target.category for target in self.targets).items()))

    def counts_by_status(self) -> dict[str, int]:
        return dict(sorted(Counter(target.coverage_status for target in self.targets).items()))

    def counts_by_tier(self) -> dict[str, int]:
        return dict(sorted(Counter(target.priority_tier for target in self.targets).items()))

    def funnel_counts(self) -> dict[str, int]:
        stage_index = {stage: index for index, stage in enumerate(COVERAGE_STAGES)}
        return {
            stage: sum(
                1
                for target in self.targets
                if target.coverage_status in stage_index
                and stage_index[target.coverage_status] >= stage_index[stage]
            )
            for stage in COVERAGE_STAGES
        }


def load_coverage_manifest(path: str | Path, *, version: str) -> CoverageManifest:
    path = Path(path)
    return parse_coverage_manifest_csv(path.read_text(encoding="utf-8-sig"), version=version)


def parse_coverage_manifest_csv(csv_text: str, *, version: str) -> CoverageManifest:
    normalized_version = version.strip()
    if not normalized_version:
        raise CoverageManifestError("Manifest version is required.")

    reader = csv.DictReader(io.StringIO(csv_text))
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or ())]
    if missing_columns:
        raise CoverageManifestError(f"Missing manifest columns: {', '.join(missing_columns)}")

    targets: list[CoverageTarget] = []
    errors: list[str] = []
    seen_keys: set[str] = set()
    seen_concepts: dict[tuple[str, str, str], str] = {}

    for row_number, raw_row in enumerate(reader, start=2):
        target, row_errors = _parse_target(raw_row, row_number=row_number)
        errors.extend(row_errors)
        if target is None:
            continue

        if target.target_key in seen_keys:
            errors.append(f"row {row_number}: duplicate target_key '{target.target_key}'")
        else:
            seen_keys.add(target.target_key)

        previous_key = seen_concepts.get(target.concept_identity)
        if previous_key:
            errors.append(
                f"row {row_number}: duplicate concept for '{previous_key}' and '{target.target_key}'"
            )
        else:
            seen_concepts[target.concept_identity] = target.target_key
        targets.append(target)

    if errors:
        raise CoverageManifestError("Invalid coverage manifest:\n- " + "\n- ".join(errors))

    canonical_text = _canonical_manifest_text(targets)
    return CoverageManifest(
        version=normalized_version,
        targets=tuple(targets),
        sha256=hashlib.sha256(canonical_text.encode("utf-8")).hexdigest(),
    )


def _parse_target(
    raw_row: Mapping[str, str | None],
    *,
    row_number: int,
) -> tuple[CoverageTarget | None, tuple[str, ...]]:
    values = {column: _clean(raw_row.get(column)) for column in REQUIRED_COLUMNS}
    errors: list[str] = []

    for field_name in (
        "target_key",
        "preferred_name_es",
        "category",
        "subcategory",
        "preparation_state",
        "priority_tier",
        "chile_relevance",
        "expected_source",
        "mapping_status",
        "coverage_status",
    ):
        if not values[field_name]:
            errors.append(f"{field_name} is required")

    if values["target_key"] and not _TARGET_KEY_RE.fullmatch(values["target_key"]):
        errors.append("target_key must be lowercase kebab-case")

    _validate_choice(values, "category", CATEGORIES, errors)
    _validate_choice(values, "preparation_state", PREPARATION_STATES, errors)
    _validate_choice(values, "priority_tier", PRIORITY_TIERS, errors)
    _validate_choice(values, "chile_relevance", CHILE_RELEVANCE_VALUES, errors)
    _validate_choice(values, "expected_source", EXPECTED_SOURCES, errors)
    _validate_choice(values, "mapping_status", MAPPING_STATUSES, errors)
    _validate_choice(values, "coverage_status", COVERAGE_STATUSES, errors)

    if values["priority_tier"] == "discovery" and not values["discovery_origin"]:
        errors.append("discovery_origin is required for discovery targets")
    if values["coverage_status"] in {"deferred", "excluded"} and not values["decision_reason"]:
        errors.append("decision_reason is required for deferred or excluded targets")

    stage_index = {stage: index for index, stage in enumerate(COVERAGE_STAGES)}
    current_stage = stage_index.get(values["coverage_status"], -1)
    if current_stage >= stage_index["source_mapped"]:
        if values["mapping_status"] != "mapped":
            errors.append("source_mapped or later targets require mapping_status=mapped")
        for field_name in ("source_food_id", "source_dataset", "source_version"):
            if not values[field_name]:
                errors.append(f"{field_name} is required at source_mapped or later")
        if values["expected_source"] == "unmapped":
            errors.append("expected_source cannot be unmapped at source_mapped or later")
    if current_stage >= stage_index["imported"] and not values["catalog_food_id"]:
        errors.append("catalog_food_id is required at imported or later")

    if errors:
        return None, tuple(f"row {row_number}: {error}" for error in errors)
    return CoverageTarget(**values), ()


def _validate_choice(
    values: Mapping[str, str],
    field_name: str,
    allowed: Iterable[str],
    errors: list[str],
) -> None:
    value = values[field_name]
    if value and value not in allowed:
        errors.append(f"{field_name} has unsupported value '{value}'")


def _canonical_manifest_text(targets: Iterable[CoverageTarget]) -> str:
    return "\n".join(
        "|".join(getattr(target, column) for column in REQUIRED_COLUMNS)
        for target in sorted(targets, key=lambda item: item.target_key)
    )


def _normalize_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).split())


def _clean(value: str | None) -> str:
    return str(value or "").strip()


__all__ = [
    "CATEGORIES",
    "CHILE_RELEVANCE_VALUES",
    "COVERAGE_STAGES",
    "COVERAGE_STATUSES",
    "CoverageManifest",
    "CoverageManifestError",
    "CoverageTarget",
    "EXPECTED_SOURCES",
    "MAPPING_STATUSES",
    "PREPARATION_STATES",
    "PRIORITY_TIERS",
    "REQUIRED_COLUMNS",
    "load_coverage_manifest",
    "parse_coverage_manifest_csv",
]
