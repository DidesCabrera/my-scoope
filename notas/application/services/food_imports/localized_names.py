from dataclasses import dataclass

from notas.application.services.food_imports.normalization import normalize_food_name
from notas.domain.models import Food, FoodLocalizedName


@dataclass(frozen=True)
class FoodLocalizedNameInput:
    name: str
    language: str = "es"
    country: str = ""
    is_primary: bool = True


@dataclass(frozen=True)
class EnsureFoodLocalizedNamesResult:
    created_count: int
    updated_count: int
    skipped_count: int


def ensure_food_localized_names(
    *,
    food: Food,
    localized_names: list[FoodLocalizedNameInput],
) -> EnsureFoodLocalizedNamesResult:
    """
    Ensure localized display names exist for a food.

    This service is idempotent:
    - empty names are skipped
    - existing localized names are not duplicated
    - existing names can be updated when is_primary changes
    - normalized_name is generated consistently

    It does not modify the Food itself.
    """

    created_count = 0
    updated_count = 0
    skipped_count = 0

    for localized_name_input in localized_names:
        display_name = _clean_display_name(localized_name_input.name)

        if not display_name:
            skipped_count += 1
            continue

        language = _clean_language(localized_name_input.language)
        country = _clean_country(localized_name_input.country)
        normalized_name = normalize_food_name(display_name)

        localized_name, created = FoodLocalizedName.objects.get_or_create(
            food=food,
            normalized_name=normalized_name,
            language=language,
            country=country,
            defaults={
                "name": display_name,
                "is_primary": localized_name_input.is_primary,
            },
        )

        if created:
            created_count += 1
            continue

        if (
            localized_name.name != display_name
            or localized_name.is_primary != localized_name_input.is_primary
        ):
            localized_name.name = display_name
            localized_name.is_primary = localized_name_input.is_primary
            localized_name.save(
                update_fields=[
                    "name",
                    "is_primary",
                ]
            )
            updated_count += 1
            continue

        skipped_count += 1

    return EnsureFoodLocalizedNamesResult(
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
    )


def get_primary_food_localized_name(
    *,
    food: Food,
    language: str = "es",
    country: str = "CL",
) -> str:
    """
    Return the primary localized display name for a food.

    Fallback order:
    1. exact language + country primary name
    2. language-only primary name
    3. empty string

    When a caller prefetched the lightweight display-name subset into
    ``_prefetched_primary_display_names``, resolve from memory to avoid one
    localized-name query per food in list/detail render loops.
    """

    normalized_language = _clean_language(language)
    normalized_country = _clean_country(country)

    prefetched_names = getattr(food, "_prefetched_primary_display_names", None)

    if prefetched_names is not None:
        exact_match = _find_prefetched_primary_name(
            prefetched_names,
            language=normalized_language,
            country=normalized_country,
        )

        if exact_match:
            return exact_match

        language_match = _find_prefetched_primary_name(
            prefetched_names,
            language=normalized_language,
            country="",
        )

        if language_match:
            return language_match

        return ""

    exact_match = (
        food.localized_names
        .filter(
            language=normalized_language,
            country=normalized_country,
            is_primary=True,
        )
        .order_by("name")
        .first()
    )

    if exact_match:
        return exact_match.name

    language_match = (
        food.localized_names
        .filter(
            language=normalized_language,
            country="",
            is_primary=True,
        )
        .order_by("name")
        .first()
    )

    if language_match:
        return language_match.name

    return ""


def resolve_food_display_name(
    food: Food,
    *,
    language: str = "es",
    country: str = "CL",
) -> str:
    """
    Return the user-facing display name for a food.

    Fallback order:
    1. primary localized name for language + country
    2. primary localized name for language only
    3. original food.name
    """

    localized_name = get_primary_food_localized_name(
        food=food,
        language=language,
        country=country,
    )

    return localized_name or food.name


def _find_prefetched_primary_name(
    localized_names,
    *,
    language: str,
    country: str,
) -> str:
    matches = [
        localized_name.name
        for localized_name in localized_names
        if (
            localized_name.language == language
            and localized_name.country == country
            and localized_name.is_primary
        )
    ]

    return sorted(matches)[0] if matches else ""


def _clean_display_name(value: str | None) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _clean_language(value: str | None) -> str:
    if not value:
        return "es"

    return str(value).strip().lower() or "es"


def _clean_country(value: str | None) -> str:
    if not value:
        return ""

    return str(value).strip().upper()