"""Internal snapshot protocol from Food Catalog to ``notas.Food``.

This module is the only application bridge that may read ``food_catalog`` in
order to materialize published catalog data into the operational food model.
It does not expose Food Catalog to MCP and it does not make ``CatalogFood`` an
operational nutrition source.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from food_catalog.application.contracts import (
    CandidateSourceType,
    CatalogEvidenceItem,
    CatalogServingOption,
    NutrientProfilePer100g,
    OperationalFoodSnapshotPayload,
    PublishedFoodSnapshot,
)
from food_catalog.application.solver_readiness import build_catalog_solver_profile
from food_catalog.models import CatalogFood
from notas.application.services.food_imports.aliases import (
    FoodAliasInput,
    ensure_food_aliases,
)
from notas.domain.models import Food, FoodPortion


FOOD_CATALOG_PORTION_SOURCE = "food_catalog"


class FoodCatalogSnapshotError(ValueError):
    """Raised when a catalog food cannot be materialized as ``notas.Food``."""


class CatalogFoodNotPublishedError(FoodCatalogSnapshotError):
    """Raised when trying to snapshot a non-published catalog food."""


@dataclass(frozen=True)
class OperationalFoodSnapshotResult:
    """Result of a Food Catalog -> ``notas.Food`` snapshot write."""

    food: Food
    created_portions: int
    created_aliases: int
    skipped_aliases: int


@dataclass(frozen=True)
class MarkFoodCatalogSnapshotStaleResult:
    """Result of marking an operational Food snapshot as stale."""

    food: Food


def build_operational_food_snapshot_payload(
    catalog_food: CatalogFood | int,
) -> OperationalFoodSnapshotPayload:
    """Build a contract payload from a published ``CatalogFood``.

    The payload is not operational by itself. It becomes operational only after
    this module writes the copied values into ``notas.Food``.
    """

    catalog_food = _resolve_catalog_food(catalog_food)
    _ensure_published(catalog_food)

    solver_profile = build_catalog_solver_profile(catalog_food)

    snapshot = PublishedFoodSnapshot(
        catalog_ref=str(catalog_food.catalog_ref),
        catalog_version=catalog_food.catalog_version,
        display_name=catalog_food.display_name,
        canonical_name=catalog_food.canonical_name,
        food_group=catalog_food.food_group,
        food_subgroup=catalog_food.food_subgroup,
        nutrients_per_100g=NutrientProfilePer100g(
            protein_g=catalog_food.protein_g_per_100g,
            carbs_g=catalog_food.carbs_g_per_100g,
            fat_g=catalog_food.fat_g_per_100g,
            calories_kcal=catalog_food.calories_kcal_per_100g,
            fiber_g=catalog_food.fiber_g_per_100g,
            sugar_g=catalog_food.sugar_g_per_100g,
            saturated_fat_g=catalog_food.saturated_fat_g_per_100g,
            sodium_mg=catalog_food.sodium_mg_per_100g,
        ),
        data_quality_score=catalog_food.data_quality_score,
        is_verified=True,
        preparation_state=solver_profile.preparation_state,
        solver_enabled=solver_profile.solver_enabled,
        default_portion_g=solver_profile.default_portion_g,
        min_portion_g=solver_profile.min_portion_g,
        max_portion_g=solver_profile.max_portion_g,
        portion_step_g=solver_profile.portion_step_g,
        serving_options=_catalog_serving_options(catalog_food),
        aliases=_catalog_alias_names(catalog_food),
        evidence=_catalog_evidence_items(catalog_food),
    )

    return snapshot.to_operational_snapshot_payload()


@transaction.atomic
def create_operational_food_snapshot_from_catalog(
    catalog_food: CatalogFood | int,
    *,
    created_by=None,
    is_global: bool = True,
) -> OperationalFoodSnapshotResult:
    """Create a new operational ``notas.Food`` from a published ``CatalogFood``.

    The created Food stores copied nutrients and trace metadata. Downstream
    systems must use the resulting ``food.id`` only, never ``catalog_food.id``.
    """

    catalog_food = _resolve_catalog_food(catalog_food)
    payload = build_operational_food_snapshot_payload(catalog_food)
    snapshot_created_at = timezone.now()

    food = Food.objects.create(
        **payload.food_defaults(),
        created_by=created_by,
        is_global=is_global,
        list_order=_next_food_list_order(created_by) if created_by and not is_global else 0,
        **_food_catalog_trace_fields(
            catalog_food=catalog_food,
            payload=payload,
            snapshot_created_at=snapshot_created_at,
        ),
    )

    portion_count = _replace_catalog_portions(food=food, payload=payload)
    alias_result = _ensure_catalog_aliases(food=food, payload=payload)

    return OperationalFoodSnapshotResult(
        food=food,
        created_portions=portion_count,
        created_aliases=alias_result.created_count,
        skipped_aliases=alias_result.skipped_count,
    )


@transaction.atomic
def refresh_operational_food_snapshot_from_catalog(
    food: Food,
    *,
    catalog_food: CatalogFood | int | None = None,
) -> OperationalFoodSnapshotResult:
    """Refresh an existing ``notas.Food`` from its linked published catalog food.

    Refreshing changes copied values on ``notas.Food``. It never makes
    ``CatalogFood`` readable by Meals, Solver or MCP.
    """

    if catalog_food is None:
        if food.catalog_food_id is None:
            raise FoodCatalogSnapshotError("Food has no catalog_food_id to refresh from.")
        catalog_food = food.catalog_food_id

    catalog_food = _resolve_catalog_food(catalog_food)
    payload = build_operational_food_snapshot_payload(catalog_food)
    snapshot_created_at = timezone.now()

    for field_name, value in payload.food_defaults().items():
        setattr(food, field_name, value)

    for field_name, value in _food_catalog_trace_fields(
        catalog_food=catalog_food,
        payload=payload,
        snapshot_created_at=snapshot_created_at,
    ).items():
        setattr(food, field_name, value)

    food.save(
        update_fields=[
            *payload.food_defaults().keys(),
            "catalog_food_id",
            "catalog_food_ref",
            "catalog_snapshot_version",
            "catalog_snapshot_payload",
            "catalog_snapshot_created_at",
            "catalog_sync_status",
        ]
    )

    portion_count = _replace_catalog_portions(food=food, payload=payload)
    alias_result = _ensure_catalog_aliases(food=food, payload=payload)

    return OperationalFoodSnapshotResult(
        food=food,
        created_portions=portion_count,
        created_aliases=alias_result.created_count,
        skipped_aliases=alias_result.skipped_count,
    )


@transaction.atomic
def mark_operational_food_catalog_snapshot_stale(
    food: Food,
) -> MarkFoodCatalogSnapshotStaleResult:
    """Mark a catalog-backed operational Food as stale without changing macros."""

    if food.catalog_food_id is None and food.catalog_food_ref is None:
        raise FoodCatalogSnapshotError("Only catalog-backed foods can be marked stale.")

    food.catalog_sync_status = Food.CATALOG_SYNC_STALE
    food.save(update_fields=["catalog_sync_status"])

    return MarkFoodCatalogSnapshotStaleResult(food=food)


def _resolve_catalog_food(catalog_food: CatalogFood | int) -> CatalogFood:
    if isinstance(catalog_food, CatalogFood):
        return catalog_food
    return CatalogFood.objects.get(pk=catalog_food)


def _ensure_published(catalog_food: CatalogFood) -> None:
    if not catalog_food.is_published:
        raise CatalogFoodNotPublishedError(
            "Only published CatalogFood records can be materialized as notas.Food snapshots."
        )


def _catalog_serving_options(catalog_food: CatalogFood) -> tuple[CatalogServingOption, ...]:
    return tuple(
        CatalogServingOption(
            label=portion.label,
            grams=portion.grams,
            source=portion.source or FOOD_CATALOG_PORTION_SOURCE,
            is_default=portion.is_default,
        )
        for portion in catalog_food.portions.all().order_by("-is_default", "label", "id")
    )


def _catalog_alias_names(catalog_food: CatalogFood) -> tuple[str, ...]:
    return tuple(
        alias.name
        for alias in catalog_food.aliases.all().order_by("-is_primary", "name", "id")
    )


def _catalog_alias_inputs(catalog_food: CatalogFood) -> list[FoodAliasInput]:
    return [
        FoodAliasInput(
            name=alias.name,
            language=alias.language,
            country=alias.country,
        )
        for alias in catalog_food.aliases.all().order_by("-is_primary", "name", "id")
    ]


def _catalog_evidence_items(catalog_food: CatalogFood) -> tuple[CatalogEvidenceItem, ...]:
    evidence_items: list[CatalogEvidenceItem] = []

    for source in catalog_food.sources.all().order_by("source_name", "source_food_id", "id"):
        evidence_items.append(
            CatalogEvidenceItem(
                source_type=CandidateSourceType(source.source_type),
                source_name=source.source_name,
                source_food_id=source.source_food_id,
                source_dataset=source.source_dataset,
                source_version=source.source_version,
                source_url=source.source_url,
                license_name=source.license_name,
                attribution=source.attribution,
                payload_hash=source.normalized_payload_hash or source.raw_payload_hash,
            )
        )

    return tuple(evidence_items)


def _food_catalog_trace_fields(
    *,
    catalog_food: CatalogFood,
    payload: OperationalFoodSnapshotPayload,
    snapshot_created_at,
) -> dict[str, Any]:
    return {
        "catalog_food_id": catalog_food.id,
        "catalog_food_ref": catalog_food.catalog_ref,
        "catalog_snapshot_version": catalog_food.catalog_version,
        "catalog_snapshot_payload": _json_safe(
            {
                "source": "food_catalog",
                "catalog_food_id": catalog_food.id,
                "catalog_food_ref": catalog_food.catalog_ref,
                "catalog_version": catalog_food.catalog_version,
                "catalog_status": catalog_food.status,
                "snapshot_created_at": snapshot_created_at.isoformat(),
                "contract": payload.as_contract_payload(),
            }
        ),
        "catalog_snapshot_created_at": snapshot_created_at,
        "catalog_sync_status": Food.CATALOG_SYNC_SNAPSHOT,
    }


def _replace_catalog_portions(
    *,
    food: Food,
    payload: OperationalFoodSnapshotPayload,
) -> int:
    food.portions.filter(source=FOOD_CATALOG_PORTION_SOURCE).delete()

    created_count = 0
    for option in payload.serving_options:
        portion_defaults = option.operational_portion_defaults()
        portion_defaults["source"] = FOOD_CATALOG_PORTION_SOURCE
        FoodPortion.objects.create(
            food=food,
            **portion_defaults,
        )
        created_count += 1

    return created_count


def _ensure_catalog_aliases(
    *,
    food: Food,
    payload: OperationalFoodSnapshotPayload,
):
    if not food.catalog_food_id:
        return ensure_food_aliases(food=food, aliases=[])

    catalog_food = CatalogFood.objects.get(pk=food.catalog_food_id)
    return ensure_food_aliases(
        food=food,
        aliases=_catalog_alias_inputs(catalog_food),
    )


def _next_food_list_order(user) -> int:
    current_max = (
        Food.objects
        .filter(created_by=user, is_active=True)
        .aggregate(max_order=Max("list_order"))
        .get("max_order")
    )
    return (current_max or 0) + 1


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


__all__ = [
    "CatalogFoodNotPublishedError",
    "FoodCatalogSnapshotError",
    "MarkFoodCatalogSnapshotStaleResult",
    "OperationalFoodSnapshotResult",
    "build_operational_food_snapshot_payload",
    "create_operational_food_snapshot_from_catalog",
    "mark_operational_food_catalog_snapshot_stale",
    "refresh_operational_food_snapshot_from_catalog",
]
