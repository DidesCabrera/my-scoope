"""Internal Food Catalog contracts.

These contracts describe the payloads that connect the master catalog with the
operational nutrition system. They intentionally do not import Django models,
``notas`` or MCP modules.

Food Catalog may produce candidates and publication snapshots. Operational
features must still consume only ``notas.Food`` after an internal backend
protocol materializes these payloads into operational foods.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Mapping


class FoodCatalogContractError(ValueError):
    """Raised when an internal Food Catalog contract payload is invalid."""


class CandidateSourceType(StrEnum):
    """Supported high-level origin categories for catalog candidates."""

    NATURAL_VERIFIED = "natural_verified"
    BRAND_SUBMITTED = "brand_submitted"
    USER_CREATED = "user_created"
    EXTERNAL_TEMPORARY = "external_temporary"
    ADMIN_IMPORT = "admin_import"


class SourceLicenseStatus(StrEnum):
    """License/persistence status of a candidate source."""

    ALLOWED = "allowed"
    NEEDS_REVIEW = "needs_review"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class CatalogReviewStatus(StrEnum):
    """Review status for a structured food candidate."""

    EXTERNAL_CANDIDATE = "external_candidate"
    MANUAL_CANDIDATE = "manual_candidate"
    BRAND_SUBMITTED = "brand_submitted"
    NORMALIZED = "normalized"
    PENDING_REVIEW = "pending_review"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    REVIEWED = "reviewed"
    VERIFIED = "verified"
    PUBLISHED = "published"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class OperationalVisibility(StrEnum):
    """Visibility values expected by the operational ``notas.Food`` snapshot."""

    CORE = "core"
    EXTENDED = "extended"
    HIDDEN = "hidden"
    REJECTED = "rejected"


class PreparationState(StrEnum):
    """Semantic state copied into operational foods for solver safety."""

    UNKNOWN = "unknown"
    RAW = "raw"
    COOKED = "cooked"
    DRY = "dry"
    HYDRATED = "hydrated"
    READY_TO_EAT = "ready_to_eat"


def _decimal(value: Decimal | int | float | str | None, *, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:  # pragma: no cover - defensive branch
        raise FoodCatalogContractError(f"{field_name} must be decimal-compatible.") from exc


def _require_non_negative(value: Decimal | None, *, field_name: str) -> None:
    if value is not None and value < 0:
        raise FoodCatalogContractError(f"{field_name} must be greater than or equal to 0.")


def _require_positive(value: Decimal | None, *, field_name: str) -> None:
    if value is not None and value <= 0:
        raise FoodCatalogContractError(f"{field_name} must be greater than 0.")


def _require_text(value: str, *, field_name: str) -> None:
    if not value or not value.strip():
        raise FoodCatalogContractError(f"{field_name} is required.")


@dataclass(frozen=True)
class NutrientProfilePer100g:
    """Normalized macro/micro nutrient profile per 100 grams."""

    protein_g: Decimal | int | float | str
    carbs_g: Decimal | int | float | str
    fat_g: Decimal | int | float | str
    calories_kcal: Decimal | int | float | str | None = None
    fiber_g: Decimal | int | float | str | None = None
    sugar_g: Decimal | int | float | str | None = None
    saturated_fat_g: Decimal | int | float | str | None = None
    sodium_mg: Decimal | int | float | str | None = None

    def __post_init__(self) -> None:
        decimal_fields = {
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "calories_kcal": self.calories_kcal,
            "fiber_g": self.fiber_g,
            "sugar_g": self.sugar_g,
            "saturated_fat_g": self.saturated_fat_g,
            "sodium_mg": self.sodium_mg,
        }
        for field_name, value in decimal_fields.items():
            decimal_value = _decimal(value, field_name=field_name)
            _require_non_negative(decimal_value, field_name=field_name)
            object.__setattr__(self, field_name, decimal_value)

    def operational_macro_defaults(self) -> dict[str, float]:
        """Return macro fields compatible with ``notas.Food`` defaults."""

        return {
            "protein": float(self.protein_g),
            "carbs": float(self.carbs_g),
            "fat": float(self.fat_g),
        }

    def operational_micro_defaults(self) -> dict[str, Decimal | None]:
        """Return optional nutrient fields compatible with ``notas.Food`` names."""

        return {
            "fiber_g_per_100g": self.fiber_g,
            "sugar_g_per_100g": self.sugar_g,
            "saturated_fat_g_per_100g": self.saturated_fat_g,
            "sodium_mg_per_100g": self.sodium_mg,
        }


@dataclass(frozen=True)
class CatalogServingOption:
    """A serving option normalized to grams."""

    label: str
    grams: Decimal | int | float | str
    source: str = ""
    is_default: bool = False

    def __post_init__(self) -> None:
        _require_text(self.label, field_name="label")
        grams = _decimal(self.grams, field_name="grams")
        _require_positive(grams, field_name="grams")
        object.__setattr__(self, "grams", grams)

    def operational_portion_defaults(self) -> dict[str, Any]:
        """Return field names compatible with ``notas.FoodPortion`` creation."""

        return {
            "label": self.label.strip(),
            "grams": self.grams,
            "source": self.source.strip(),
            "is_default": self.is_default,
        }


@dataclass(frozen=True)
class CatalogEvidenceItem:
    """Traceable evidence attached to a catalog candidate or publication."""

    source_type: CandidateSourceType | str
    source_name: str
    source_food_id: str = ""
    source_dataset: str = ""
    source_version: str = ""
    source_url: str = ""
    license_name: str = ""
    attribution: str = ""
    payload_hash: str = ""

    def __post_init__(self) -> None:
        _require_text(self.source_name, field_name="source_name")
        object.__setattr__(self, "source_type", CandidateSourceType(self.source_type))

    def source_metadata_defaults(self) -> dict[str, str]:
        """Return traceability fields compatible with source metadata writes."""

        return {
            "source": str(self.source_type.value),
            "source_food_id": self.source_food_id,
            "source_dataset": self.source_dataset,
            "source_version": self.source_version,
            "source_url": self.source_url,
            "raw_payload_hash": self.payload_hash,
            "normalized_payload_hash": "",
            "license_name": self.license_name,
            "attribution": self.attribution,
        }


@dataclass(frozen=True)
class CatalogFoodCandidate:
    """Structured candidate ready for internal catalog review.

    A candidate is not operational. It must be reviewed and later published or
    materialized through an internal protocol before the nutrition system can use
    it as ``notas.Food``.
    """

    candidate_ref: str
    source_type: CandidateSourceType | str
    source_name: str
    source_license_status: SourceLicenseStatus | str
    display_name: str
    nutrients_per_100g: NutrientProfilePer100g
    canonical_name: str = ""
    brand_name: str = ""
    country: str = ""
    language: str = "es"
    is_branded: bool = False
    serving_options: tuple[CatalogServingOption, ...] = field(default_factory=tuple)
    aliases: tuple[str, ...] = field(default_factory=tuple)
    evidence: tuple[CatalogEvidenceItem, ...] = field(default_factory=tuple)
    confidence_score: Decimal | int | float | str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    review_status: CatalogReviewStatus | str = CatalogReviewStatus.EXTERNAL_CANDIDATE

    def __post_init__(self) -> None:
        _require_text(self.candidate_ref, field_name="candidate_ref")
        _require_text(self.source_name, field_name="source_name")
        _require_text(self.display_name, field_name="display_name")
        object.__setattr__(self, "source_type", CandidateSourceType(self.source_type))
        object.__setattr__(self, "source_license_status", SourceLicenseStatus(self.source_license_status))
        object.__setattr__(self, "review_status", CatalogReviewStatus(self.review_status))
        confidence_score = _decimal(self.confidence_score, field_name="confidence_score")
        _require_non_negative(confidence_score, field_name="confidence_score")
        if confidence_score is not None and confidence_score > 100:
            raise FoodCatalogContractError("confidence_score must be less than or equal to 100.")
        object.__setattr__(self, "confidence_score", confidence_score)
        object.__setattr__(self, "aliases", tuple(alias.strip() for alias in self.aliases if alias.strip()))
        object.__setattr__(self, "warnings", tuple(warning.strip() for warning in self.warnings if warning.strip()))

    @property
    def can_be_published_without_license_review(self) -> bool:
        """Return whether source licensing is already compatible with persistence."""

        return self.source_license_status == SourceLicenseStatus.ALLOWED


@dataclass(frozen=True)
class PublishedFoodSnapshot:
    """Stable publication snapshot emitted by Food Catalog.

    This payload is not a ``notas.Food`` instance and is not visible to MCP. A
    backend protocol may materialize it into ``notas.Food``.
    """

    catalog_ref: str
    catalog_version: str
    display_name: str
    nutrients_per_100g: NutrientProfilePer100g
    canonical_name: str = ""
    food_group: str = ""
    food_subgroup: str = ""
    data_quality_score: int = 0
    visibility: OperationalVisibility | str = OperationalVisibility.EXTENDED
    is_verified: bool = True
    default_portion_g: Decimal | int | float | str | None = None
    min_portion_g: Decimal | int | float | str | None = None
    max_portion_g: Decimal | int | float | str | None = None
    portion_step_g: Decimal | int | float | str | None = None
    preparation_state: PreparationState | str = PreparationState.UNKNOWN
    solver_enabled: bool = False
    serving_options: tuple[CatalogServingOption, ...] = field(default_factory=tuple)
    aliases: tuple[str, ...] = field(default_factory=tuple)
    evidence: tuple[CatalogEvidenceItem, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_text(self.catalog_ref, field_name="catalog_ref")
        _require_text(self.catalog_version, field_name="catalog_version")
        _require_text(self.display_name, field_name="display_name")
        if not 0 <= self.data_quality_score <= 100:
            raise FoodCatalogContractError("data_quality_score must be between 0 and 100.")
        object.__setattr__(self, "visibility", OperationalVisibility(self.visibility))
        object.__setattr__(self, "preparation_state", PreparationState(self.preparation_state))
        for field_name in ("default_portion_g", "min_portion_g", "max_portion_g", "portion_step_g"):
            value = _decimal(getattr(self, field_name), field_name=field_name)
            _require_positive(value, field_name=field_name)
            object.__setattr__(self, field_name, value)
        object.__setattr__(self, "aliases", tuple(alias.strip() for alias in self.aliases if alias.strip()))

    def to_operational_snapshot_payload(self) -> "OperationalFoodSnapshotPayload":
        """Build the payload the snapshot protocol can persist into ``notas.Food``."""

        return OperationalFoodSnapshotPayload(
            source_catalog_ref=self.catalog_ref,
            source_catalog_version=self.catalog_version,
            name=self.display_name.strip(),
            canonical_name=self.canonical_name.strip(),
            food_group=self.food_group.strip(),
            food_subgroup=self.food_subgroup.strip(),
            nutrients_per_100g=self.nutrients_per_100g,
            data_quality_score=self.data_quality_score,
            visibility=self.visibility,
            is_verified=self.is_verified,
            preparation_state=self.preparation_state,
            solver_enabled=self.solver_enabled,
            default_portion_g=self.default_portion_g,
            min_portion_g=self.min_portion_g,
            max_portion_g=self.max_portion_g,
            portion_step_g=self.portion_step_g,
            serving_options=self.serving_options,
            aliases=self.aliases,
            evidence=self.evidence,
        )


@dataclass(frozen=True)
class OperationalFoodSnapshotPayload:
    """Payload prepared for the internal ``notas.Food`` write protocol."""

    source_catalog_ref: str
    source_catalog_version: str
    name: str
    canonical_name: str
    food_group: str
    food_subgroup: str
    nutrients_per_100g: NutrientProfilePer100g
    data_quality_score: int = 0
    visibility: OperationalVisibility | str = OperationalVisibility.EXTENDED
    is_verified: bool = True
    preparation_state: PreparationState | str = PreparationState.UNKNOWN
    solver_enabled: bool = False
    default_portion_g: Decimal | None = None
    min_portion_g: Decimal | None = None
    max_portion_g: Decimal | None = None
    portion_step_g: Decimal | None = None
    serving_options: tuple[CatalogServingOption, ...] = field(default_factory=tuple)
    aliases: tuple[str, ...] = field(default_factory=tuple)
    evidence: tuple[CatalogEvidenceItem, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_text(self.source_catalog_ref, field_name="source_catalog_ref")
        _require_text(self.source_catalog_version, field_name="source_catalog_version")
        _require_text(self.name, field_name="name")
        if not 0 <= self.data_quality_score <= 100:
            raise FoodCatalogContractError("data_quality_score must be between 0 and 100.")
        object.__setattr__(self, "visibility", OperationalVisibility(self.visibility))
        object.__setattr__(self, "preparation_state", PreparationState(self.preparation_state))

    def food_defaults(self) -> dict[str, Any]:
        """Return field names compatible with ``notas.Food`` creation/update.

        The returned dictionary is a contract payload, not a direct write. The
        actual write protocol lives in the backend bridge and remains internal to
        the application layer.
        """

        return {
            "name": self.name.strip(),
            **self.nutrients_per_100g.operational_macro_defaults(),
            "canonical_name": self.canonical_name.strip(),
            "is_verified": self.is_verified,
            "is_active": True,
            "food_group": self.food_group.strip(),
            "food_subgroup": self.food_subgroup.strip(),
            "preparation_state": self.preparation_state.value,
            "solver_enabled": self.solver_enabled,
            **self.nutrients_per_100g.operational_micro_defaults(),
            "default_portion_g": self.default_portion_g,
            "min_portion_g": self.min_portion_g,
            "max_portion_g": self.max_portion_g,
            "portion_step_g": self.portion_step_g,
            "data_quality_score": self.data_quality_score,
            "visibility": self.visibility.value,
        }

    def snapshot_metadata(self) -> dict[str, Any]:
        """Return catalog traceability stored by the snapshot protocol."""

        return {
            "source_catalog_ref": self.source_catalog_ref,
            "source_catalog_version": self.source_catalog_version,
            "preparation_state": self.preparation_state.value,
            "solver_enabled": self.solver_enabled,
            "aliases": tuple(self.aliases),
            "serving_options": tuple(
                option.operational_portion_defaults() for option in self.serving_options
            ),
            "evidence": tuple(item.source_metadata_defaults() for item in self.evidence),
        }

    def as_contract_payload(self) -> Mapping[str, Any]:
        """Return a serializable-ish view for tests, logs or command dry-runs."""

        return {
            "food_defaults": self.food_defaults(),
            "snapshot_metadata": self.snapshot_metadata(),
        }


__all__ = [
    "CandidateSourceType",
    "CatalogEvidenceItem",
    "CatalogFoodCandidate",
    "CatalogReviewStatus",
    "CatalogServingOption",
    "FoodCatalogContractError",
    "NutrientProfilePer100g",
    "OperationalFoodSnapshotPayload",
    "OperationalVisibility",
    "PreparationState",
    "PublishedFoodSnapshot",
    "SourceLicenseStatus",
]
