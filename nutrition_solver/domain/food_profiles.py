from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from nutrition_solver.domain.capabilities import (
    SOLVER_CAPABILITY_SCHEMA_VERSION,
    SolverFeatureAvailability,
    SolverFeatureKey,
)
from nutrition_solver.domain.models import SolverFood


@dataclass(frozen=True)
class SolverFeatureValue:
    feature: SolverFeatureKey | str
    value: Any
    confidence: float
    source: str
    version: str = ""
    derived: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "feature", SolverFeatureKey(self.feature))
        object.__setattr__(self, "confidence", max(0.0, min(float(self.confidence), 100.0)))
        source = str(self.source or "").strip()
        if not source:
            raise ValueError("solver_feature_value_source_required")
        object.__setattr__(self, "source", source)

    @property
    def available(self) -> bool:
        return self.value is not None and self.value != "" and self.value != () and self.value != []

    def availability(self) -> SolverFeatureAvailability:
        return SolverFeatureAvailability(
            available=self.available,
            confidence=self.confidence,
            source=self.source,
            version=self.version,
        )

    def as_dict(self) -> dict[str, Any]:
        value = list(self.value) if isinstance(self.value, tuple) else self.value
        return {
            "feature": self.feature.value,
            "value": value,
            "confidence": round(self.confidence, 2),
            "source": self.source,
            "version": self.version,
            "derived": self.derived,
        }


@dataclass(frozen=True)
class SolverFoodProfile:
    food: SolverFood
    features: tuple[SolverFeatureValue, ...] = ()
    schema_version: str = SOLVER_CAPABILITY_SCHEMA_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        features = tuple(self.features or ())
        keys = [feature.feature for feature in features]
        if len(keys) != len(set(keys)):
            raise ValueError("solver_food_profile_duplicate_feature")
        object.__setattr__(self, "features", features)
        object.__setattr__(self, "metadata", dict(self.metadata or {}))

    def feature(self, key: SolverFeatureKey | str) -> SolverFeatureValue | None:
        normalized = SolverFeatureKey(key)
        return next((feature for feature in self.features if feature.feature == normalized), None)

    def availability(self) -> dict[SolverFeatureKey, SolverFeatureAvailability]:
        return {
            feature.feature: feature.availability()
            for feature in self.features
        }

    @property
    def functional_roles(self) -> tuple[str, ...]:
        feature = self.feature(SolverFeatureKey.FUNCTIONAL_ROLES)
        return _normalized_strings(feature.value if feature else ())

    @property
    def meal_affinities(self) -> tuple[str, ...]:
        feature = self.feature(SolverFeatureKey.MEAL_AFFINITIES)
        return _normalized_strings(feature.value if feature else ())

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "food": {
                "food_id": self.food.food_id,
                "name": self.food.name,
                "role": self.food.role,
            },
            "features": [feature.as_dict() for feature in self.features],
            "metadata": dict(self.metadata),
        }


def derive_macro_role_features(food: SolverFood, *, source: str = "macro_role_rules.v1") -> SolverFeatureValue:
    kcal = max(float(food.kcal_per_100g), 1.0)
    ratios = {
        "primary_protein": float(food.protein_per_100g) * 4 / kcal,
        "starch_or_carbohydrate": float(food.carbs_per_100g) * 4 / kcal,
        "added_or_dense_fat": float(food.fat_per_100g) * 9 / kcal,
    }
    ordered = [name for name, ratio in sorted(ratios.items(), key=lambda item: item[1], reverse=True) if ratio >= 0.20]
    if food.role == "vegetable" and "vegetable" not in ordered:
        ordered.insert(0, "vegetable")
    if not ordered:
        ordered.append("mixed_food")

    return SolverFeatureValue(
        feature=SolverFeatureKey.FUNCTIONAL_ROLES,
        value=tuple(ordered),
        confidence=55,
        source=source,
        version="v1",
        derived=True,
    )


def _normalized_strings(values: Any) -> tuple[str, ...]:
    if isinstance(values, str):
        values = (values,)
    return tuple(
        normalized
        for value in (values or ())
        if (normalized := str(value).strip().lower())
    )
