"""Publication guards for master Food Catalog records.

The master catalog is not operational data. Publishing a ``CatalogFood`` only
makes it eligible for the explicit snapshot protocol that materializes a stable
``notas.Food`` copy later. These guards keep the curation boundary strict before
any admin action can mark catalog records as published.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from food_catalog.application.solver_readiness import check_catalog_food_solver_ready
from food_catalog.models import CatalogFood, CatalogFoodPortion, CatalogFoodSource

MIN_PUBLISH_QUALITY_SCORE = 70
PUBLISHABLE_STATUSES = (
    CatalogFood.STATUS_REVIEWED,
    CatalogFood.STATUS_VERIFIED,
)
MAX_MACRO_SUM_PER_100G = Decimal("120.000")
MAX_SODIUM_MG_PER_100G = Decimal("100000.000")


@dataclass(frozen=True)
class CatalogPublicationCheck:
    """Result of checking whether a catalog food can be published."""

    can_publish: bool
    errors: tuple[str, ...] = ()


def check_catalog_food_publishable(catalog_food: CatalogFood) -> CatalogPublicationCheck:
    """Return publication errors for a ``CatalogFood``.

    This intentionally validates only master-catalog governance concerns. It
    does not materialize ``notas.Food`` and does not expose Food Catalog to MCP,
    Solver, Meals, DailyPlans, Programs or Comparators.
    """

    errors: list[str] = []

    if catalog_food.status not in PUBLISHABLE_STATUSES:
        errors.append("status must be reviewed or verified before publication")

    if not catalog_food.display_name.strip():
        errors.append("display_name is required")

    if not catalog_food.canonical_name.strip():
        errors.append("canonical_name is required")

    if catalog_food.data_quality_score < MIN_PUBLISH_QUALITY_SCORE:
        errors.append(
            f"data_quality_score must be at least {MIN_PUBLISH_QUALITY_SCORE}"
        )

    macro_fields = {
        "protein_g_per_100g": catalog_food.protein_g_per_100g,
        "carbs_g_per_100g": catalog_food.carbs_g_per_100g,
        "fat_g_per_100g": catalog_food.fat_g_per_100g,
    }

    for field_name, value in macro_fields.items():
        if value is None:
            errors.append(f"{field_name} is required")
        elif value < 0:
            errors.append(f"{field_name} cannot be negative")
        elif value > 100:
            errors.append(f"{field_name} cannot exceed 100 g per 100 g")

    if all(value is not None for value in macro_fields.values()):
        macro_sum = sum(macro_fields.values(), Decimal("0.000"))
        if macro_sum > MAX_MACRO_SUM_PER_100G:
            errors.append("protein + carbs + fat cannot exceed 120 g per 100 g")

    if catalog_food.calories_kcal_per_100g is not None and catalog_food.calories_kcal_per_100g < 0:
        errors.append("calories_kcal_per_100g cannot be negative")

    if catalog_food.sodium_mg_per_100g is not None:
        if catalog_food.sodium_mg_per_100g < 0:
            errors.append("sodium_mg_per_100g cannot be negative")
        elif catalog_food.sodium_mg_per_100g > MAX_SODIUM_MG_PER_100G:
            errors.append("sodium_mg_per_100g is outside the accepted sanity range")

    if not catalog_food.sources.exists():
        errors.append("at least one traceable source is required")
    elif not _has_publishable_source(catalog_food):
        errors.append("at least one source with allowed or reviewed license is required")

    if not catalog_food.portions.exists():
        errors.append("at least one serving/portion option is required")
    elif not _has_default_portion(catalog_food):
        errors.append("one serving/portion option must be marked as default")

    if catalog_food.solver_enabled:
        solver_check = check_catalog_food_solver_ready(catalog_food)
        if not solver_check.is_ready:
            errors.extend(f"solver readiness: {error}" for error in solver_check.errors)

    return CatalogPublicationCheck(
        can_publish=not errors,
        errors=tuple(errors),
    )


def _has_publishable_source(catalog_food: CatalogFood) -> bool:
    return CatalogFoodSource.objects.filter(
        catalog_food=catalog_food,
        license_status__in=(
            CatalogFoodSource.LICENSE_ALLOWED,
            CatalogFoodSource.LICENSE_NEEDS_REVIEW,
        ),
    ).exists()


def _has_default_portion(catalog_food: CatalogFood) -> bool:
    return CatalogFoodPortion.objects.filter(
        catalog_food=catalog_food,
        is_default=True,
    ).exists()
