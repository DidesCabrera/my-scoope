"""Persistence service for the built-in core natural foods seed."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from food_catalog.application.core_natural_foods import (
    CORE_NATURAL_FOODS_ATTRIBUTION,
    CORE_NATURAL_FOODS_DATASET,
    CORE_NATURAL_FOODS_SEED_VERSION,
    CORE_NATURAL_FOODS_SOURCE_NAME,
    CoreNaturalFoodSeed,
    core_natural_foods_seed_sha256,
    load_core_natural_foods_seed,
    validate_core_natural_foods_seed,
)
from food_catalog.application.imports.normalization import normalize_food_name
from food_catalog.infrastructure.imports.governance import (
    catalog_import_identity,
    start_catalog_import_batch,
)
from food_catalog.models import (
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
    CatalogImportBatch,
)


@dataclass(frozen=True)
class CoreNaturalFoodsSeedPlan:
    total_rows: int
    valid_rows: int
    invalid_rows: int
    to_create: int
    to_update: int
    validation_errors: tuple[str, ...]


@dataclass(frozen=True)
class CoreNaturalFoodsSeedApplyResult:
    batch: CatalogImportBatch
    total_rows: int
    created_rows: int
    updated_rows: int


def dry_run_core_natural_foods_seed() -> CoreNaturalFoodsSeedPlan:
    foods = load_core_natural_foods_seed()
    validation = validate_core_natural_foods_seed(foods)

    if not validation.is_valid:
        return CoreNaturalFoodsSeedPlan(
            total_rows=validation.foods_count,
            valid_rows=0,
            invalid_rows=validation.foods_count,
            to_create=0,
            to_update=0,
            validation_errors=validation.errors,
        )

    source_ids = [_source_food_id(food) for food in foods]
    existing_source_ids = set(
        CatalogFoodSource.objects.filter(
            source_name=CORE_NATURAL_FOODS_SOURCE_NAME,
            source_food_id__in=source_ids,
        ).values_list("source_food_id", flat=True)
    )
    existing_canonical_names = set(
        CatalogFood.objects.filter(
            canonical_name__in=[food.canonical_name for food in foods],
            brand_name="",
            country="CL",
        ).values_list("canonical_name", flat=True)
    )

    to_update = 0
    to_create = 0
    for food in foods:
        if _source_food_id(food) in existing_source_ids or food.canonical_name in existing_canonical_names:
            to_update += 1
        else:
            to_create += 1

    return CoreNaturalFoodsSeedPlan(
        total_rows=len(foods),
        valid_rows=len(foods),
        invalid_rows=0,
        to_create=to_create,
        to_update=to_update,
        validation_errors=(),
    )


def core_natural_foods_seed_identity():
    return catalog_import_identity(
        source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
        source_name=CORE_NATURAL_FOODS_SOURCE_NAME,
        source_version=CORE_NATURAL_FOODS_SEED_VERSION,
        input_sha256=core_natural_foods_seed_sha256(),
        parameters_payload={"dataset": CORE_NATURAL_FOODS_DATASET, "publish": False},
    )


@transaction.atomic
def apply_core_natural_foods_seed(
    *,
    dry_run_batch: CatalogImportBatch,
    requested_by=None,
    reason: str,
) -> CoreNaturalFoodsSeedApplyResult:
    foods = load_core_natural_foods_seed()
    validation = validate_core_natural_foods_seed(foods)
    if not validation.is_valid:
        raise ValueError("Invalid core natural foods seed: " + " | ".join(validation.errors))

    batch = start_catalog_import_batch(
        identity=core_natural_foods_seed_identity(),
        dry_run_batch=dry_run_batch,
        total_rows=len(foods),
        requested_by=requested_by,
        reason=reason,
    )
    created_rows = 0
    updated_rows = 0

    for food_seed in foods:
        catalog_food, created = _upsert_catalog_food(food_seed)
        _upsert_source(catalog_food, food_seed, import_batch=batch)
        _sync_portions(catalog_food, food_seed)
        _sync_aliases(catalog_food, food_seed)

        if created:
            created_rows += 1
        else:
            updated_rows += 1

    batch.imported_rows = created_rows + updated_rows
    batch.status = CatalogImportBatch.STATUS_COMPLETED
    batch.finished_at = timezone.now()
    batch.summary_payload = {"created": created_rows, "updated": updated_rows, "published": 0}
    batch.save(update_fields=["imported_rows", "status", "finished_at", "summary_payload"])

    return CoreNaturalFoodsSeedApplyResult(
        batch=batch,
        total_rows=len(foods),
        created_rows=created_rows,
        updated_rows=updated_rows,
    )


def _upsert_catalog_food(food_seed: CoreNaturalFoodSeed) -> tuple[CatalogFood, bool]:
    source_food_id = _source_food_id(food_seed)
    existing_source = CatalogFoodSource.objects.filter(
        source_name=CORE_NATURAL_FOODS_SOURCE_NAME,
        source_food_id=source_food_id,
    ).select_related("catalog_food").first()

    defaults = {
        "catalog_version": CORE_NATURAL_FOODS_SEED_VERSION,
        "display_name": food_seed.display_name,
        "canonical_name": food_seed.canonical_name,
        "brand_name": "",
        "is_branded": False,
        "language": "es",
        "country": "CL",
        "food_group": food_seed.food_group,
        "food_subgroup": food_seed.food_subgroup,
        "preparation_state": food_seed.preparation_state,
        "solver_enabled": True,
        "solver_min_portion_g": None,
        "solver_max_portion_g": None,
        "solver_portion_step_g": None,
        "protein_g_per_100g": food_seed.protein_g_per_100g,
        "carbs_g_per_100g": food_seed.carbs_g_per_100g,
        "fat_g_per_100g": food_seed.fat_g_per_100g,
        "calories_kcal_per_100g": food_seed.calories_kcal_per_100g,
        "fiber_g_per_100g": food_seed.fiber_g_per_100g,
        "sugar_g_per_100g": food_seed.sugar_g_per_100g,
        "sodium_mg_per_100g": food_seed.sodium_mg_per_100g,
        "source_type": CatalogFood.SOURCE_NATURAL_VERIFIED,
        "status": CatalogFood.STATUS_VERIFIED,
        "data_quality_score": 95,
        "confidence_score": Decimal("95.00"),
    }

    if existing_source:
        catalog_food = existing_source.catalog_food
        for field, value in defaults.items():
            setattr(catalog_food, field, value)
        catalog_food.save(update_fields=[*defaults.keys(), "updated_at"])
        return catalog_food, False

    catalog_food, created = CatalogFood.objects.update_or_create(
        canonical_name=food_seed.canonical_name,
        brand_name="",
        country="CL",
        defaults=defaults,
    )
    return catalog_food, created


def _upsert_source(
    catalog_food: CatalogFood,
    food_seed: CoreNaturalFoodSeed,
    *,
    import_batch: CatalogImportBatch,
) -> None:
    CatalogFoodSource.objects.update_or_create(
        source_name=CORE_NATURAL_FOODS_SOURCE_NAME,
        source_food_id=_source_food_id(food_seed),
        defaults={
            "catalog_food": catalog_food,
            "import_batch": import_batch,
            "source_type": CatalogFood.SOURCE_NATURAL_VERIFIED,
            "source_dataset": CORE_NATURAL_FOODS_DATASET,
            "source_version": CORE_NATURAL_FOODS_SEED_VERSION,
            "license_name": "internal-curated",
            "license_status": CatalogFoodSource.LICENSE_ALLOWED,
            "attribution": CORE_NATURAL_FOODS_ATTRIBUTION,
            "evidence_payload": {
                "seed_id": food_seed.seed_id,
                "dataset": CORE_NATURAL_FOODS_DATASET,
                "version": CORE_NATURAL_FOODS_SEED_VERSION,
                "review_note": "Core natural food selected for launch-readiness seed.",
                "preparation_state": food_seed.preparation_state,
                "solver_enabled": True,
            },
        },
    )


def _sync_portions(catalog_food: CatalogFood, food_seed: CoreNaturalFoodSeed) -> None:
    seen_labels: set[str] = set()
    for portion in food_seed.portions:
        seen_labels.add(portion.label)
        CatalogFoodPortion.objects.update_or_create(
            catalog_food=catalog_food,
            label=portion.label,
            defaults={
                "grams": portion.grams,
                "source": CORE_NATURAL_FOODS_DATASET,
                "is_default": portion.is_default,
            },
        )

    CatalogFoodPortion.objects.filter(catalog_food=catalog_food).exclude(
        label__in=seen_labels,
    ).delete()


def _sync_aliases(catalog_food: CatalogFood, food_seed: CoreNaturalFoodSeed) -> None:
    alias_names = {food_seed.display_name, food_seed.canonical_name, *food_seed.aliases}
    for alias_name in sorted(alias_names):
        normalized_name = normalize_food_name(alias_name)
        if not normalized_name:
            continue
        CatalogFoodAlias.objects.update_or_create(
            catalog_food=catalog_food,
            normalized_name=normalized_name,
            language="es",
            country="CL",
            defaults={
                "name": alias_name,
                "alias_type": CatalogFoodAlias.ALIAS_SEARCH,
                "is_primary": normalized_name == food_seed.canonical_name,
            },
        )


def _source_food_id(food_seed: CoreNaturalFoodSeed) -> str:
    return f"core-natural:{food_seed.seed_id}"
