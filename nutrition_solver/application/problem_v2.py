from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Mapping

from nutrition_solver.application.contracts import SolverConstraint
from nutrition_solver.domain.food_profiles import SolverFoodProfile
from nutrition_solver.domain.meal_grammar import MealArchetype


class ObjectiveTier(IntEnum):
    FEASIBILITY = 0
    NUTRITION = 10
    FUNCTIONAL = 20
    PREFERENCE = 30
    SIMPLICITY = 40


@dataclass(frozen=True)
class NutrientRange:
    metric: str
    preferred: float
    minimum: float
    maximum: float
    weight: float = 1.0

    def __post_init__(self) -> None:
        minimum = float(self.minimum)
        preferred = float(self.preferred)
        maximum = float(self.maximum)
        if minimum > preferred or preferred > maximum:
            raise ValueError("nutrient_range_order_invalid")
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "preferred", preferred)
        object.__setattr__(self, "maximum", maximum)
        object.__setattr__(self, "weight", max(float(self.weight), 0.0))

    def as_dict(self) -> dict[str, float | str]:
        return {
            "metric": self.metric,
            "preferred": self.preferred,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "weight": self.weight,
        }


@dataclass(frozen=True)
class MealSlotProblem:
    slot_id: str
    meal_kind: str
    nutrient_ranges: tuple[NutrientRange, ...]
    allowed_archetypes: tuple[MealArchetype, ...]

    def __post_init__(self) -> None:
        if not str(self.slot_id or "").strip():
            raise ValueError("meal_slot_problem_id_required")
        if not self.allowed_archetypes:
            raise ValueError("meal_slot_problem_requires_archetype")


@dataclass(frozen=True)
class OptimizationProblemV2:
    food_profiles: tuple[SolverFoodProfile, ...]
    meal_slots: tuple[MealSlotProblem, ...]
    daily_nutrient_ranges: tuple[NutrientRange, ...] = ()
    constraints: tuple[SolverConstraint, ...] = ()
    preferences: Mapping[str, Any] = field(default_factory=dict)
    time_limit_ms: int = 1500
    deterministic_seed: int = 0

    def __post_init__(self) -> None:
        if not self.food_profiles:
            raise ValueError("optimization_problem_v2_requires_food_profiles")
        if not self.meal_slots:
            raise ValueError("optimization_problem_v2_requires_meal_slots")
        slot_ids = [slot.slot_id for slot in self.meal_slots]
        if len(slot_ids) != len(set(slot_ids)):
            raise ValueError("optimization_problem_v2_duplicate_slot")
        object.__setattr__(self, "time_limit_ms", max(50, min(int(self.time_limit_ms), 10_000)))
        object.__setattr__(self, "preferences", dict(self.preferences or {}))

    def as_dict(self) -> dict[str, Any]:
        return {
            "food_profiles": [profile.as_dict() for profile in self.food_profiles],
            "meal_slots": [
                {
                    "slot_id": slot.slot_id,
                    "meal_kind": slot.meal_kind,
                    "nutrient_ranges": [item.as_dict() for item in slot.nutrient_ranges],
                    "allowed_archetypes": [item.as_dict() for item in slot.allowed_archetypes],
                }
                for slot in self.meal_slots
            ],
            "daily_nutrient_ranges": [item.as_dict() for item in self.daily_nutrient_ranges],
            "constraints": [item.as_dict() for item in self.constraints],
            "preferences": dict(self.preferences),
            "time_limit_ms": self.time_limit_ms,
            "deterministic_seed": self.deterministic_seed,
        }
