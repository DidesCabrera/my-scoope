"""Contracts and validation for the built-in core natural foods seed."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from importlib import resources
from typing import Any

from food_catalog.application.imports.normalization import normalize_food_name

CORE_NATURAL_FOODS_SEED_VERSION = "2026-07-fc03"
CORE_NATURAL_FOODS_DATASET = "core_natural_foods_es_cl_v1"
CORE_NATURAL_FOODS_SOURCE_NAME = "MyScoope Core Natural Foods Seed"
CORE_NATURAL_FOODS_ATTRIBUTION = (
    "MyScoope internal core natural foods seed. Values are normalized per 100 g "
    "and must remain reviewable before operational use."
)


@dataclass(frozen=True)
class CoreFoodPortionSeed:
    label: str
    grams: Decimal
    is_default: bool = False


@dataclass(frozen=True)
class CoreNaturalFoodSeed:
    seed_id: str
    display_name: str
    canonical_name: str
    food_group: str
    food_subgroup: str
    preparation_state: str
    protein_g_per_100g: Decimal
    carbs_g_per_100g: Decimal
    fat_g_per_100g: Decimal
    calories_kcal_per_100g: Decimal | None
    fiber_g_per_100g: Decimal | None
    sugar_g_per_100g: Decimal | None
    sodium_mg_per_100g: Decimal | None
    default_portion_g: Decimal
    portions: tuple[CoreFoodPortionSeed, ...]
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class CoreNaturalFoodsSeedValidation:
    is_valid: bool
    errors: tuple[str, ...]
    foods_count: int


def load_core_natural_foods_seed() -> tuple[CoreNaturalFoodSeed, ...]:
    """Load the packaged ES/CL-oriented core natural foods seed."""

    data_file = resources.files("food_catalog.data").joinpath(
        "core_natural_foods_es_cl_v1.json"
    )
    rows = json.loads(data_file.read_text(encoding="utf-8"))
    return tuple(_parse_seed_row(row) for row in rows)


def core_natural_foods_seed_sha256() -> str:
    data_file = resources.files("food_catalog.data").joinpath(
        "core_natural_foods_es_cl_v1.json"
    )
    return hashlib.sha256(data_file.read_bytes()).hexdigest()


def validate_core_natural_foods_seed(
    foods: tuple[CoreNaturalFoodSeed, ...] | None = None,
) -> CoreNaturalFoodsSeedValidation:
    """Validate seed integrity before dry-run/apply commands touch the DB."""

    foods = foods if foods is not None else load_core_natural_foods_seed()
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_canonical_names: set[str] = set()

    for food in foods:
        prefix = food.seed_id or food.display_name or "(unknown seed row)"

        if not food.seed_id:
            errors.append("seed_id is required")
        elif food.seed_id in seen_ids:
            errors.append(f"duplicate seed_id: {food.seed_id}")
        seen_ids.add(food.seed_id)

        if not food.display_name.strip():
            errors.append(f"{prefix}: display_name is required")

        if food.preparation_state not in {
            "raw",
            "cooked",
            "dry",
            "hydrated",
            "ready_to_eat",
        }:
            errors.append(f"{prefix}: preparation_state must be explicit for the core seed")

        normalized_canonical = normalize_food_name(food.canonical_name)
        if not normalized_canonical:
            errors.append(f"{prefix}: canonical_name is required")
        elif normalized_canonical in seen_canonical_names:
            errors.append(f"{prefix}: duplicate canonical_name: {normalized_canonical}")
        seen_canonical_names.add(normalized_canonical)

        for field_name, value in {
            "protein_g_per_100g": food.protein_g_per_100g,
            "carbs_g_per_100g": food.carbs_g_per_100g,
            "fat_g_per_100g": food.fat_g_per_100g,
        }.items():
            if value < 0:
                errors.append(f"{prefix}: {field_name} cannot be negative")
            if value > 100:
                errors.append(f"{prefix}: {field_name} cannot exceed 100")

        macro_sum = food.protein_g_per_100g + food.carbs_g_per_100g + food.fat_g_per_100g
        if macro_sum > Decimal("120"):
            errors.append(f"{prefix}: protein + carbs + fat cannot exceed 120 g per 100 g")

        if food.default_portion_g <= 0:
            errors.append(f"{prefix}: default_portion_g must be positive")

        default_portions = [portion for portion in food.portions if portion.is_default]
        if len(default_portions) != 1:
            errors.append(f"{prefix}: exactly one portion must be default")

        for portion in food.portions:
            if not portion.label.strip():
                errors.append(f"{prefix}: portion label is required")
            if portion.grams <= 0:
                errors.append(f"{prefix}: portion {portion.label} grams must be positive")

    return CoreNaturalFoodsSeedValidation(
        is_valid=not errors,
        errors=tuple(errors),
        foods_count=len(foods),
    )


def _parse_seed_row(row: dict[str, Any]) -> CoreNaturalFoodSeed:
    portions = tuple(
        CoreFoodPortionSeed(
            label=str(portion[0]).strip(),
            grams=_decimal(portion[1]),
            is_default=bool(portion[2]),
        )
        for portion in row.get("portions", ())
    )

    return CoreNaturalFoodSeed(
        seed_id=str(row.get("id", "")).strip(),
        display_name=str(row.get("display_name", "")).strip(),
        canonical_name=normalize_food_name(str(row.get("canonical_name", "")).strip()),
        food_group=str(row.get("food_group", "")).strip(),
        food_subgroup=str(row.get("food_subgroup", "")).strip(),
        preparation_state=str(row.get("preparation_state", "unknown")).strip() or "unknown",
        protein_g_per_100g=_decimal(row.get("protein_g_per_100g")),
        carbs_g_per_100g=_decimal(row.get("carbs_g_per_100g")),
        fat_g_per_100g=_decimal(row.get("fat_g_per_100g")),
        calories_kcal_per_100g=_optional_decimal(row.get("calories_kcal_per_100g")),
        fiber_g_per_100g=_optional_decimal(row.get("fiber_g_per_100g")),
        sugar_g_per_100g=_optional_decimal(row.get("sugar_g_per_100g")),
        sodium_mg_per_100g=_optional_decimal(row.get("sodium_mg_per_100g")),
        default_portion_g=_decimal(row.get("default_portion_g")),
        portions=portions,
        aliases=tuple(str(alias).strip() for alias in row.get("aliases", ()) if str(alias).strip()),
    )


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.001"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.000")


def _optional_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    return _decimal(value)
