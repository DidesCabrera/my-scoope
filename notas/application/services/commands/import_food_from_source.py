from dataclasses import dataclass

from django.db import transaction

from notas.application.dto.imported_food_dto import ImportedFoodDTO
from notas.application.services.food_imports.normalization import normalize_imported_food
from notas.application.services.food_imports.quality import evaluate_imported_food_quality
from notas.application.services.food_imports.visibility_policy import (
    resolve_initial_food_visibility,
)
from notas.domain.models import Food, FoodSourceMetadata


@dataclass(frozen=True)
class ImportFoodFromSourceResult:
    food: Food | None
    created: bool
    skipped: bool
    reason: str = ""


def import_food_from_source(dto: ImportedFoodDTO) -> ImportFoodFromSourceResult:
    """
    Create a global Food from an external source DTO.

    This command is intentionally source-agnostic. USDA, Open Food Facts,
    LATINFOODS or manual importers should map their data into ImportedFoodDTO
    before calling this command.

    Data safety rules:
    - Existing user foods are not modified.
    - Existing foods with the same source + source_food_id are not duplicated.
    - Imported foods are global, not user-owned.
    - Imported foods start unverified.
    - Imported foods are normalized and quality-checked before creation.
    """

    normalized_dto = normalize_imported_food(dto)

    quality_result = evaluate_imported_food_quality(normalized_dto)
    if not quality_result.is_valid:
        return ImportFoodFromSourceResult(
            food=None,
            created=False,
            skipped=True,
            reason=quality_result.reason,
        )
    
    initial_visibility = resolve_initial_food_visibility(
        quality_score=quality_result.score,
    )

    existing_metadata = FoodSourceMetadata.objects.select_related("food").filter(
        source=normalized_dto.source,
        source_food_id=normalized_dto.source_food_id,
    ).first()

    if existing_metadata:
        return ImportFoodFromSourceResult(
            food=existing_metadata.food,
            created=False,
            skipped=True,
            reason="already_imported",
        )

    with transaction.atomic():
        food = Food.objects.create(
            name=normalized_dto.name,
            canonical_name=normalized_dto.canonical_name,
            protein=float(normalized_dto.protein),
            carbs=float(normalized_dto.carbs),
            fat=float(normalized_dto.fat),
            created_by=None,
            is_global=True,
            is_verified=False,
            is_active=True,
            food_group=normalized_dto.food_group,
            food_subgroup=normalized_dto.food_subgroup,
            fiber_g_per_100g=normalized_dto.fiber_g_per_100g,
            sugar_g_per_100g=normalized_dto.sugar_g_per_100g,
            saturated_fat_g_per_100g=normalized_dto.saturated_fat_g_per_100g,
            sodium_mg_per_100g=normalized_dto.sodium_mg_per_100g,
            visibility=initial_visibility,
            data_quality_score=quality_result.score,
        )

        FoodSourceMetadata.objects.create(
            food=food,
            source=normalized_dto.source,
            source_food_id=normalized_dto.source_food_id,
            source_dataset=normalized_dto.source_dataset,
            source_version=normalized_dto.source_version,
            source_url=normalized_dto.source_url,
            raw_payload_hash=normalized_dto.raw_payload_hash,
            normalized_payload_hash=normalized_dto.normalized_payload_hash,
            license_name=normalized_dto.license_name,
            attribution=normalized_dto.attribution,
        )

    return ImportFoodFromSourceResult(
        food=food,
        created=True,
        skipped=False,
    )