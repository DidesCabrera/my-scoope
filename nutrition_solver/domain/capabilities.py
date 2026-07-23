from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


SOLVER_CAPABILITY_SCHEMA_VERSION = "solver_food_capabilities.v1"


class SolverFeatureKey(StrEnum):
    NUTRIENTS = "nutrients"
    PORTION_BOUNDS = "portion_bounds"
    PREPARATION_STATE = "preparation_state"
    FOOD_FORM = "food_form"
    FUNCTIONAL_ROLES = "functional_roles"
    MEAL_AFFINITIES = "meal_affinities"
    NATURAL_SERVING = "natural_serving"
    DIETARY_TAGS = "dietary_tags"
    ALLERGENS = "allergens"
    PREPARATION_EFFORT = "preparation_effort"
    COST_BAND = "cost_band"


class MissingFeatureBehavior(StrEnum):
    EXCLUDE_CANDIDATE = "exclude_candidate"
    IMPOSSIBLE_RESULT = "impossible_result"
    WARN_AND_CONTINUE = "warn_and_continue"
    NEUTRAL_DEFAULT = "neutral_default"


@dataclass(frozen=True)
class SolverFeatureRequirement:
    feature: SolverFeatureKey | str
    required: bool = False
    minimum_confidence: float = 0.0
    missing_behavior: MissingFeatureBehavior | str = MissingFeatureBehavior.NEUTRAL_DEFAULT

    def __post_init__(self) -> None:
        object.__setattr__(self, "feature", SolverFeatureKey(self.feature))
        confidence = max(0.0, min(float(self.minimum_confidence), 100.0))
        object.__setattr__(self, "minimum_confidence", confidence)
        behavior = MissingFeatureBehavior(self.missing_behavior)
        if self.required and behavior in {
            MissingFeatureBehavior.NEUTRAL_DEFAULT,
            MissingFeatureBehavior.WARN_AND_CONTINUE,
        }:
            behavior = MissingFeatureBehavior.EXCLUDE_CANDIDATE
        object.__setattr__(self, "missing_behavior", behavior)

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature.value,
            "required": self.required,
            "minimum_confidence": round(self.minimum_confidence, 2),
            "missing_behavior": self.missing_behavior.value,
        }


@dataclass(frozen=True)
class SolverFeatureRequirements:
    profile: str
    requirements: tuple[SolverFeatureRequirement, ...]
    schema_version: str = SOLVER_CAPABILITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        profile = str(self.profile or "").strip()
        if not profile:
            raise ValueError("solver_feature_requirements_profile_required")
        object.__setattr__(self, "profile", profile)
        normalized = tuple(self.requirements or ())
        keys = [requirement.feature for requirement in normalized]
        if len(keys) != len(set(keys)):
            raise ValueError("solver_feature_requirements_duplicate_feature")
        object.__setattr__(self, "requirements", normalized)

    @property
    def required_features(self) -> tuple[SolverFeatureKey, ...]:
        return tuple(item.feature for item in self.requirements if item.required)

    @property
    def optional_features(self) -> tuple[SolverFeatureKey, ...]:
        return tuple(item.feature for item in self.requirements if not item.required)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile": self.profile,
            "requirements": [item.as_dict() for item in self.requirements],
        }


@dataclass(frozen=True)
class SolverFeatureAvailability:
    available: bool
    confidence: float = 0.0
    source: str = ""
    version: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", max(0.0, min(float(self.confidence), 100.0)))


@dataclass(frozen=True)
class SolverFeatureAssessment:
    is_eligible: bool
    missing_required: tuple[str, ...] = ()
    low_confidence_required: tuple[str, ...] = ()
    unavailable_optional: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "is_eligible": self.is_eligible,
            "missing_required": list(self.missing_required),
            "low_confidence_required": list(self.low_confidence_required),
            "unavailable_optional": list(self.unavailable_optional),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


def assess_solver_feature_requirements(
    requirements: SolverFeatureRequirements,
    availability: Mapping[SolverFeatureKey | str, SolverFeatureAvailability],
) -> SolverFeatureAssessment:
    normalized = {
        SolverFeatureKey(key): value
        for key, value in availability.items()
    }
    missing_required: list[str] = []
    low_confidence_required: list[str] = []
    unavailable_optional: list[str] = []
    warnings: list[str] = []

    for requirement in requirements.requirements:
        current = normalized.get(requirement.feature)
        is_available = bool(current and current.available)
        confidence_ok = bool(current and current.confidence >= requirement.minimum_confidence)

        if requirement.required and not is_available:
            missing_required.append(requirement.feature.value)
            continue
        if requirement.required and not confidence_ok:
            low_confidence_required.append(requirement.feature.value)
            continue
        if not requirement.required and (not is_available or not confidence_ok):
            unavailable_optional.append(requirement.feature.value)
            if requirement.missing_behavior == MissingFeatureBehavior.WARN_AND_CONTINUE:
                warnings.append(f"optional_feature_unavailable:{requirement.feature.value}")

    return SolverFeatureAssessment(
        is_eligible=not missing_required and not low_confidence_required,
        missing_required=tuple(missing_required),
        low_confidence_required=tuple(low_confidence_required),
        unavailable_optional=tuple(unavailable_optional),
        warnings=tuple(warnings),
        metadata={
            "profile": requirements.profile,
            "schema_version": requirements.schema_version,
        },
    )


DEFAULT_MEAL_OPTIMIZATION_FEATURES = SolverFeatureRequirements(
    profile="meal_optimization.v1",
    requirements=(
        SolverFeatureRequirement(SolverFeatureKey.NUTRIENTS, required=True, minimum_confidence=70),
        SolverFeatureRequirement(SolverFeatureKey.PORTION_BOUNDS, required=True, minimum_confidence=60),
        SolverFeatureRequirement(
            SolverFeatureKey.PREPARATION_STATE,
            required=True,
            minimum_confidence=50,
        ),
        SolverFeatureRequirement(
            SolverFeatureKey.FUNCTIONAL_ROLES,
            minimum_confidence=40,
            missing_behavior=MissingFeatureBehavior.WARN_AND_CONTINUE,
        ),
        SolverFeatureRequirement(
            SolverFeatureKey.MEAL_AFFINITIES,
            minimum_confidence=40,
            missing_behavior=MissingFeatureBehavior.WARN_AND_CONTINUE,
        ),
    ),
)
