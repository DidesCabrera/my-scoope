"""Solver-readiness helpers for master Food Catalog records.

These checks keep optimization-specific assumptions explicit before a catalog
food is published and materialized as ``notas.Food``. They do not expose
``CatalogFood`` to the solver; they only prepare safe snapshot payloads for the
existing Food Catalog -> operational Food bridge.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from food_catalog.models import CatalogFood

MIN_SOLVER_QUALITY_SCORE = 70


@dataclass(frozen=True)
class CatalogSolverProfile:
    """Portion and semantic profile copied to operational foods."""

    default_portion_g: Decimal | None
    min_portion_g: Decimal | None
    max_portion_g: Decimal | None
    portion_step_g: Decimal | None
    preparation_state: str
    solver_enabled: bool


@dataclass(frozen=True)
class CatalogSolverReadinessCheck:
    """Result of checking whether a catalog food is solver-ready."""

    is_ready: bool
    profile: CatalogSolverProfile
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def check_catalog_food_solver_ready(catalog_food: CatalogFood) -> CatalogSolverReadinessCheck:
    """Return solver-readiness errors for a master catalog food.

    A food can still be curated or published with ``solver_enabled=False``. When
    the flag is true, this check verifies that semantic state and portion bounds
    are explicit enough to become a safe future optimization candidate after the
    snapshot protocol creates/refreshes ``notas.Food``.
    """

    profile = build_catalog_solver_profile(catalog_food)
    errors: list[str] = []
    warnings: list[str] = []

    if not catalog_food.solver_enabled:
        return CatalogSolverReadinessCheck(
            is_ready=False,
            profile=profile,
            errors=("solver_enabled is false",),
        )

    if catalog_food.data_quality_score < MIN_SOLVER_QUALITY_SCORE:
        errors.append(f"data_quality_score must be at least {MIN_SOLVER_QUALITY_SCORE}")

    if not catalog_food.food_group.strip():
        errors.append("food_group is required for solver-enabled foods")

    if catalog_food.preparation_state == CatalogFood.PREPARATION_UNKNOWN:
        errors.append("preparation_state must be explicit for solver-enabled foods")

    if profile.default_portion_g is None:
        errors.append("a default portion is required for solver-enabled foods")

    if profile.min_portion_g is None:
        errors.append("minimum solver portion could not be inferred")

    if profile.max_portion_g is None:
        errors.append("maximum solver portion could not be inferred")

    if profile.portion_step_g is None:
        errors.append("portion step could not be inferred")

    if profile.min_portion_g is not None and profile.default_portion_g is not None:
        if profile.min_portion_g > profile.default_portion_g:
            errors.append("minimum solver portion cannot exceed default portion")

    if profile.max_portion_g is not None and profile.default_portion_g is not None:
        if profile.max_portion_g < profile.default_portion_g:
            errors.append("maximum solver portion cannot be lower than default portion")

    if profile.min_portion_g is not None and profile.max_portion_g is not None:
        if profile.min_portion_g > profile.max_portion_g:
            errors.append("minimum solver portion cannot exceed maximum portion")

    if profile.portion_step_g is not None and profile.portion_step_g <= 0:
        errors.append("portion step must be positive")

    if catalog_food.preparation_state in {
        CatalogFood.PREPARATION_RAW,
        CatalogFood.PREPARATION_DRY,
    }:
        warnings.append(
            "raw/dry foods are solver-ready only if the intended edible/cooked context is explicit"
        )

    return CatalogSolverReadinessCheck(
        is_ready=not errors,
        profile=profile,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def build_catalog_solver_profile(catalog_food: CatalogFood) -> CatalogSolverProfile:
    """Build explicit/defaulted solver portion metadata for snapshot payloads."""

    default_portion = _default_portion_g(catalog_food)
    portion_values = tuple(
        portion.grams for portion in catalog_food.portions.all().order_by("grams", "id")
    )

    min_portion = catalog_food.solver_min_portion_g
    if min_portion is None:
        min_portion = min(portion_values) if portion_values else None
        if min_portion == default_portion and default_portion is not None:
            min_portion = _quantize(default_portion * Decimal("0.50"))

    max_portion = catalog_food.solver_max_portion_g
    if max_portion is None:
        max_portion = max(portion_values) if portion_values else None
        if max_portion == default_portion and default_portion is not None:
            max_portion = _quantize(default_portion * Decimal("2.50"))

    portion_step = catalog_food.solver_portion_step_g
    if portion_step is None and default_portion is not None:
        portion_step = _infer_step(default_portion)

    return CatalogSolverProfile(
        default_portion_g=default_portion,
        min_portion_g=_quantize_or_none(min_portion),
        max_portion_g=_quantize_or_none(max_portion),
        portion_step_g=_quantize_or_none(portion_step),
        preparation_state=catalog_food.preparation_state,
        solver_enabled=catalog_food.solver_enabled,
    )


def _default_portion_g(catalog_food: CatalogFood) -> Decimal | None:
    default_portion = catalog_food.portions.filter(is_default=True).order_by("id").first()
    return default_portion.grams if default_portion else None


def _infer_step(default_portion_g: Decimal) -> Decimal:
    if default_portion_g <= Decimal("10.000"):
        return Decimal("1.000")
    if default_portion_g <= Decimal("100.000"):
        return Decimal("5.000")
    return Decimal("10.000")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"))


def _quantize_or_none(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return _quantize(value)
