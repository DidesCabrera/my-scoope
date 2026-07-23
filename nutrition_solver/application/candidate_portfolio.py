from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any, Mapping

from nutrition_solver.domain.food_profiles import SolverFoodProfile
from nutrition_solver.domain.meal_grammar import MealArchetype, assess_meal_grammar


@dataclass(frozen=True)
class RankedCandidate:
    profile: SolverFoodProfile
    matched_roles: tuple[str, ...]
    score: float
    reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "food_id": self.profile.food.food_id,
            "matched_roles": list(self.matched_roles),
            "score": round(self.score, 4),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class CandidateCombination:
    profiles: tuple[SolverFoodProfile, ...]
    score: float
    archetype: str
    reasons: tuple[str, ...] = ()

    @property
    def food_ids(self) -> tuple[int, ...]:
        return tuple(profile.food.food_id for profile in self.profiles)

    def as_dict(self) -> dict[str, Any]:
        return {
            "food_ids": list(self.food_ids),
            "score": round(self.score, 4),
            "archetype": self.archetype,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class CandidatePortfolio:
    archetype: str
    role_groups: Mapping[str, tuple[RankedCandidate, ...]] = field(default_factory=dict)
    combinations: tuple[CandidateCombination, ...] = ()
    diagnostics: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "archetype": self.archetype,
            "role_groups": {
                key: [candidate.as_dict() for candidate in candidates]
                for key, candidates in self.role_groups.items()
            },
            "combinations": [combination.as_dict() for combination in self.combinations],
            "diagnostics": list(self.diagnostics),
        }


def build_candidate_portfolio(
    profiles: tuple[SolverFoodProfile, ...] | list[SolverFoodProfile],
    archetype: MealArchetype,
    *,
    meal_kind: str = "",
    excluded_food_ids: tuple[int, ...] | list[int] = (),
    preferred_food_ids: tuple[int, ...] | list[int] = (),
    top_k_per_group: int = 6,
    combination_limit: int = 30,
) -> CandidatePortfolio:
    """Build a bounded, deterministic portfolio before portion optimization.

    A food may satisfy more than one functional role. Pools are therefore made
    from archetype role groups, not exclusive food categories. Only complete,
    grammar-valid combinations are returned.
    """

    excluded = {int(food_id) for food_id in excluded_food_ids}
    preferred = {int(food_id) for food_id in preferred_food_ids}
    available = tuple(
        profile
        for profile in profiles
        if profile.food.food_id not in excluded
        and not _has_incompatible_form(profile, archetype)
    )
    group_pools: dict[str, tuple[RankedCandidate, ...]] = {}
    diagnostics: list[str] = []

    for index, role_group in enumerate(archetype.required_role_groups):
        group_key = f"required_{index}"
        candidates = tuple(
            sorted(
                (
                    _rank_candidate(profile, role_group, meal_kind, preferred)
                    for profile in available
                    if set(profile.functional_roles).intersection(role_group)
                ),
                key=lambda item: (-item.score, item.profile.food.food_id),
            )[: max(1, int(top_k_per_group))]
        )
        group_pools[group_key] = candidates
        if not candidates:
            diagnostics.append(f"candidate_group_empty:{group_key}")

    if diagnostics:
        return CandidatePortfolio(
            archetype=archetype.key,
            role_groups=group_pools,
            diagnostics=tuple(diagnostics),
        )

    combinations_by_ids: dict[tuple[int, ...], CandidateCombination] = {}
    for selection in product(*(group_pools[key] for key in group_pools)):
        profiles_by_id = {candidate.profile.food.food_id: candidate.profile for candidate in selection}
        if len(profiles_by_id) != len(selection):
            continue
        selected_profiles = tuple(profiles_by_id[key] for key in sorted(profiles_by_id))
        assessment = assess_meal_grammar(archetype, selected_profiles)
        if not assessment.is_valid:
            continue
        score = sum(candidate.score for candidate in selection)
        reasons = tuple(
            sorted({reason for candidate in selection for reason in candidate.reasons})
        )
        food_ids = tuple(profile.food.food_id for profile in selected_profiles)
        combinations_by_ids[food_ids] = CandidateCombination(
            profiles=selected_profiles,
            score=score,
            archetype=archetype.key,
            reasons=reasons,
        )

    combinations = tuple(
        sorted(
            combinations_by_ids.values(),
            key=lambda item: (-item.score, item.food_ids),
        )[: max(1, int(combination_limit))]
    )
    if not combinations:
        diagnostics.append("candidate_portfolio_has_no_complete_combination")

    return CandidatePortfolio(
        archetype=archetype.key,
        role_groups=group_pools,
        combinations=combinations,
        diagnostics=tuple(diagnostics),
    )


def _rank_candidate(
    profile: SolverFoodProfile,
    role_group: tuple[str, ...],
    meal_kind: str,
    preferred: set[int],
) -> RankedCandidate:
    matched = tuple(sorted(set(profile.functional_roles).intersection(role_group)))
    role_feature = profile.feature("functional_roles")
    score = float(role_feature.confidence if role_feature else 0.0)
    reasons = [f"covers:{role}" for role in matched]
    normalized_meal_kind = str(meal_kind or "").strip().lower()
    if normalized_meal_kind and normalized_meal_kind in profile.meal_affinities:
        score += 15.0
        reasons.append("meal_affinity")
    if profile.food.food_id in preferred:
        score += 25.0
        reasons.append("preferred_food")
    return RankedCandidate(profile=profile, matched_roles=matched, score=score, reasons=tuple(reasons))


def _has_incompatible_form(profile: SolverFoodProfile, archetype: MealArchetype) -> bool:
    food_form = profile.feature("food_form")
    if not food_form or not food_form.available:
        return False
    return str(food_form.value).strip().lower() in archetype.incompatible_food_forms
