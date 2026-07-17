from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from nutrition_solver.domain.food_profiles import SolverFoodProfile


@dataclass(frozen=True)
class MealArchetype:
    key: str
    meal_kinds: tuple[str, ...]
    required_role_groups: tuple[tuple[str, ...], ...]
    optional_roles: tuple[str, ...] = ()
    minimum_components: int = 2
    maximum_components: int = 5
    incompatible_food_forms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        key = str(self.key or "").strip()
        if not key:
            raise ValueError("meal_archetype_key_required")
        if self.minimum_components < 1 or self.maximum_components < self.minimum_components:
            raise ValueError("meal_archetype_component_bounds_invalid")
        object.__setattr__(self, "key", key)

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "meal_kinds": list(self.meal_kinds),
            "required_role_groups": [list(group) for group in self.required_role_groups],
            "optional_roles": list(self.optional_roles),
            "minimum_components": self.minimum_components,
            "maximum_components": self.maximum_components,
            "incompatible_food_forms": list(self.incompatible_food_forms),
        }


@dataclass(frozen=True)
class MealGrammarAssessment:
    is_valid: bool
    archetype: str
    missing_role_groups: tuple[tuple[str, ...], ...] = ()
    component_count: int = 0
    warnings: tuple[str, ...] = ()
    role_coverage: Mapping[str, tuple[int, ...]] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "archetype": self.archetype,
            "missing_role_groups": [list(group) for group in self.missing_role_groups],
            "component_count": self.component_count,
            "warnings": list(self.warnings),
            "role_coverage": {key: list(value) for key, value in self.role_coverage.items()},
        }


MAIN_PLATE = MealArchetype(
    key="main_plate",
    meal_kinds=("main", "dinner"),
    required_role_groups=(
        ("primary_protein", "supporting_protein"),
        ("starch_or_carbohydrate", "mixed_food"),
    ),
    optional_roles=("vegetable", "added_or_dense_fat", "supporting_fat"),
    minimum_components=2,
    maximum_components=5,
    incompatible_food_forms=("beverage",),
)

BREAKFAST_COMPOSITION = MealArchetype(
    key="breakfast_composition",
    meal_kinds=("breakfast",),
    required_role_groups=(
        ("primary_protein", "supporting_protein", "mixed_food"),
        ("starch_or_carbohydrate", "fruit", "mixed_food"),
    ),
    optional_roles=("added_or_dense_fat", "supporting_fat"),
    minimum_components=2,
    maximum_components=4,
)

SNACK_PAIR = MealArchetype(
    key="snack_pair",
    meal_kinds=("snack",),
    required_role_groups=(
        ("primary_protein", "supporting_protein", "mixed_food"),
        ("starch_or_carbohydrate", "fruit", "mixed_food", "added_or_dense_fat"),
    ),
    optional_roles=("supporting_fat",),
    minimum_components=2,
    maximum_components=3,
)

DEFAULT_MEAL_ARCHETYPES = (MAIN_PLATE, BREAKFAST_COMPOSITION, SNACK_PAIR)


def assess_meal_grammar(
    archetype: MealArchetype,
    profiles: tuple[SolverFoodProfile, ...] | list[SolverFoodProfile],
) -> MealGrammarAssessment:
    profiles = tuple(profiles or ())
    role_coverage: dict[str, list[int]] = {}
    warnings: list[str] = []

    for profile in profiles:
        for role in profile.functional_roles:
            role_coverage.setdefault(role, []).append(profile.food.food_id)

    missing = tuple(
        group
        for group in archetype.required_role_groups
        if not any(role in role_coverage for role in group)
    )
    component_count = len(profiles)
    if component_count < archetype.minimum_components:
        warnings.append("meal_grammar_too_few_components")
    if component_count > archetype.maximum_components:
        warnings.append("meal_grammar_too_many_components")

    return MealGrammarAssessment(
        is_valid=not missing and not warnings,
        archetype=archetype.key,
        missing_role_groups=missing,
        component_count=component_count,
        warnings=tuple(warnings),
        role_coverage={key: tuple(ids) for key, ids in role_coverage.items()},
    )


def archetypes_for_meal_kind(meal_kind: str) -> tuple[MealArchetype, ...]:
    normalized = str(meal_kind or "").strip().lower()
    return tuple(archetype for archetype in DEFAULT_MEAL_ARCHETYPES if normalized in archetype.meal_kinds)
