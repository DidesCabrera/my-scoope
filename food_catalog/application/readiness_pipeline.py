"""Deterministic policy proposals for source-complete catalog foods.

Codex authors and versions these policies. Runtime generation is deliberately
deterministic so repeated catalog waves do not require hand-built manifests.
No proposal changes nutrition, curation status, publication, or snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

READINESS_POLICY_VERSION = "catalog-readiness.cl.v1"
MANDATORY_INTERNAL_FIELDS = (
    "default_portion_g",
    "solver_min_portion_g",
    "solver_max_portion_g",
    "solver_portion_step_g",
    "solver_enabled",
    "food_form",
    "functional_roles",
    "meal_affinities",
    "preparation_effort",
    "cost_band",
)

@dataclass(frozen=True)
class ReadinessDecision:
    profile_key: str
    default_portion_g: Decimal
    portion_label: str
    minimum_g: Decimal
    maximum_g: Decimal
    step_g: Decimal
    food_form: str
    functional_roles: tuple[str, ...]
    meal_affinities: tuple[str, ...]
    preparation_effort: str
    cost_band: str
    evidence_references: tuple[str, ...]


def decide_readiness(food, source) -> ReadinessDecision:
    portion_g, portion_label = _default_portion(food, source)
    group = food.food_group.lower()
    subgroup = food.food_subgroup.lower()

    source_reference = (
        f"{source.source_name} {source.source_dataset} {source.source_version} "
        f"food {source.source_food_id}"
    ).strip()
    evidence = tuple(filter(None, (source_reference, source.source_url)))

    if "fruit" in group:
        roles = ["fruit"]
        if subgroup in {"pome", "berries", "citrus"}:
            roles.append("fiber_source")
        elif subgroup == "tropical":
            roles.append("carbohydrate_source")
        return ReadinessDecision(
            profile_key="fruit_by_weight", default_portion_g=portion_g, portion_label=portion_label,
            minimum_g=Decimal("40"), maximum_g=max(Decimal("350"), portion_g), step_g=Decimal("10"),
            food_form="ingredient", functional_roles=tuple(roles),
            meal_affinities=("breakfast", "snack"), preparation_effort="none", cost_band="medium",
            evidence_references=evidence,
        )

    if "vegetable" in group:
        return ReadinessDecision(
            profile_key="low_density_vegetable", default_portion_g=portion_g, portion_label=portion_label,
            minimum_g=Decimal("30"), maximum_g=max(Decimal("300"), portion_g), step_g=Decimal("10"),
            food_form="ingredient", functional_roles=("vegetable", "fiber_source"),
            meal_affinities=("lunch", "dinner"), preparation_effort="low", cost_band="low",
            evidence_references=evidence,
        )

    if "fish" in group or "shellfish" in subgroup:
        return ReadinessDecision(
            profile_key="cooked_animal_protein", default_portion_g=portion_g, portion_label=portion_label,
            minimum_g=Decimal("50"), maximum_g=max(Decimal("300"), portion_g), step_g=Decimal("10"),
            food_form="ingredient", functional_roles=("lean_protein",),
            meal_affinities=("lunch", "dinner"), preparation_effort="none", cost_band="high",
            evidence_references=evidence,
        )

    raise ValueError(f"No readiness policy for {food.display_name} ({food.food_group}/{food.food_subgroup}).")


def _default_portion(food, source) -> tuple[Decimal, str]:
    existing = food.portions.filter(is_default=True).order_by("id").first()
    if existing is not None:
        return existing.grams, existing.label or "porción predeterminada existente"

    candidates = (source.evidence_payload or {}).get("source_portions", [])
    ranked = sorted(
        (row for row in candidates if _positive_decimal(row.get("grams")) is not None),
        key=_portion_rank,
    )
    if not ranked:
        raise ValueError(f"Source {source.source_food_id} has no usable household portion.")
    selected = ranked[0]
    label = " ".join(filter(None, (str(selected.get("amount", "")), selected.get("modifier", "")))).strip()
    return _positive_decimal(selected["grams"]), label or "porción de fuente"


def _portion_rank(row) -> tuple[int, Decimal]:
    label = f"{row.get('modifier', '')} {row.get('measure_unit', '')}".lower()
    preferences = ("nlea", "medium", "cup", "taza", "oz", "portion", "serving")
    rank = next((index for index, term in enumerate(preferences) if term in label), len(preferences))
    return rank, _positive_decimal(row.get("grams")) or Decimal("999999")


def _positive_decimal(value) -> Decimal | None:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


__all__ = [
    "MANDATORY_INTERNAL_FIELDS", "READINESS_POLICY_VERSION", "ReadinessDecision",
    "decide_readiness",
]
