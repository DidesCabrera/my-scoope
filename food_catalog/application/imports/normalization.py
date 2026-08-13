import re
import unicodedata
from decimal import Decimal, InvalidOperation

from food_catalog.application.imports.contracts import ImportedFoodDTO


def normalize_imported_food(dto: ImportedFoodDTO) -> ImportedFoodDTO:
    """
    Return a normalized ImportedFoodDTO without mutating the original DTO.

    This service is source-agnostic. USDA, Open Food Facts and LATINFOODS
    importers should map their source data into ImportedFoodDTO before this
    normalization step.

    Current responsibilities:
    - Trim text fields.
    - Collapse repeated spaces.
    - Normalize canonical names.
    - Normalize source/group keys.
    - Convert numeric values to Decimal.
    """

    normalized_name = _clean_display_text(dto.name)
    canonical_name = dto.canonical_name or normalized_name

    return ImportedFoodDTO(
        source=_clean_key(dto.source),
        source_food_id=_clean_display_text(dto.source_food_id),
        source_dataset=_clean_key(dto.source_dataset),
        source_version=_clean_display_text(dto.source_version),
        name=normalized_name,
        canonical_name=normalize_food_name(canonical_name),
        protein=_to_decimal(dto.protein),
        carbs=_to_decimal(dto.carbs),
        fat=_to_decimal(dto.fat),
        calories_kcal_per_100g=_to_optional_decimal(dto.calories_kcal_per_100g),
        food_group=_clean_key(dto.food_group),
        food_subgroup=_clean_key(dto.food_subgroup),
        preparation_state=_clean_key(dto.preparation_state) or "unknown",
        fiber_g_per_100g=_to_optional_decimal(dto.fiber_g_per_100g),
        sugar_g_per_100g=_to_optional_decimal(dto.sugar_g_per_100g),
        saturated_fat_g_per_100g=_to_optional_decimal(dto.saturated_fat_g_per_100g),
        sodium_mg_per_100g=_to_optional_decimal(dto.sodium_mg_per_100g),
        license_name=_clean_display_text(dto.license_name),
        attribution=_clean_display_text(dto.attribution),
        source_url=_clean_display_text(dto.source_url),
        raw_payload_hash=_clean_display_text(dto.raw_payload_hash),
        normalized_payload_hash=_clean_display_text(dto.normalized_payload_hash),
        source_description=_clean_display_text(dto.source_description),
        source_data_type=_clean_display_text(dto.source_data_type),
        source_portions=tuple(dto.source_portions),
    )


def normalize_food_name(value: str) -> str:
    """
    Normalize a food name for search and deduplication.

    Example:
    "  Avena   Integral Ácida  " -> "avena integral acida"
    """

    value = _clean_display_text(value)
    value = _strip_accents(value)
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s\-]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _clean_display_text(value: str | None) -> str:
    if value is None:
        return ""

    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _clean_key(value: str | None) -> str:
    value = normalize_food_name(value or "")
    value = value.replace("-", "_")
    value = value.replace(" ", "_")
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _to_optional_decimal(value) -> Decimal | None:
    if value is None:
        return None

    if value == "":
        return None

    return _to_decimal(value)
