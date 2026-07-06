"""Pure contracts for external Food Catalog providers.

External providers are lookup surfaces, not master catalog storage. These DTOs
let infrastructure clients return normalized search/detail payloads without
turning provider data into ``CatalogFood`` automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


class ExternalFoodProviderError(RuntimeError):
    """Raised when an external food provider cannot complete a request."""


class ExternalFoodProviderConfigurationError(ExternalFoodProviderError):
    """Raised when provider credentials or settings are missing."""


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _decimal_or_none(value: Decimal | int | float | str | None) -> Decimal | None:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise ExternalFoodProviderError(f"Invalid decimal value from external provider: {value!r}") from exc


@dataclass(frozen=True)
class ExternalFoodSearchResult:
    """Normalized result returned by an external provider search.

    A search result is only a lookup candidate. It must not be treated as a
    curated ``CatalogFood`` or operational ``notas.Food`` by itself.
    """

    provider: str
    external_food_id: str
    name: str
    brand_name: str = ""
    description: str = ""
    source_url: str = ""
    attribution_text: str = ""
    raw_payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_text(self.provider):
            raise ExternalFoodProviderError("provider is required.")
        if not _clean_text(self.external_food_id):
            raise ExternalFoodProviderError("external_food_id is required.")
        if not _clean_text(self.name):
            raise ExternalFoodProviderError("name is required.")
        object.__setattr__(self, "provider", _clean_text(self.provider))
        object.__setattr__(self, "external_food_id", _clean_text(self.external_food_id))
        object.__setattr__(self, "name", _clean_text(self.name))
        object.__setattr__(self, "brand_name", _clean_text(self.brand_name))
        object.__setattr__(self, "description", _clean_text(self.description))
        object.__setattr__(self, "source_url", _clean_text(self.source_url))
        object.__setattr__(self, "attribution_text", _clean_text(self.attribution_text))


@dataclass(frozen=True)
class ExternalFoodServing:
    """Normalized serving returned by an external provider detail endpoint."""

    provider: str
    external_food_id: str
    external_serving_id: str = ""
    serving_description: str = ""
    metric_serving_amount: Decimal | int | float | str | None = None
    metric_serving_unit: str = ""
    grams: Decimal | int | float | str | None = None
    calories_kcal: Decimal | int | float | str | None = None
    protein_g: Decimal | int | float | str | None = None
    carbs_g: Decimal | int | float | str | None = None
    fat_g: Decimal | int | float | str | None = None
    raw_payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_text(self.provider):
            raise ExternalFoodProviderError("provider is required.")
        if not _clean_text(self.external_food_id):
            raise ExternalFoodProviderError("external_food_id is required.")
        object.__setattr__(self, "provider", _clean_text(self.provider))
        object.__setattr__(self, "external_food_id", _clean_text(self.external_food_id))
        object.__setattr__(self, "external_serving_id", _clean_text(self.external_serving_id))
        object.__setattr__(self, "serving_description", _clean_text(self.serving_description))
        object.__setattr__(self, "metric_serving_unit", _clean_text(self.metric_serving_unit))
        object.__setattr__(self, "metric_serving_amount", _decimal_or_none(self.metric_serving_amount))
        object.__setattr__(self, "grams", _decimal_or_none(self.grams))
        object.__setattr__(self, "calories_kcal", _decimal_or_none(self.calories_kcal))
        object.__setattr__(self, "protein_g", _decimal_or_none(self.protein_g))
        object.__setattr__(self, "carbs_g", _decimal_or_none(self.carbs_g))
        object.__setattr__(self, "fat_g", _decimal_or_none(self.fat_g))


@dataclass(frozen=True)
class ExternalFoodDetail:
    """Normalized detail payload for one external food."""

    provider: str
    external_food_id: str
    name: str
    brand_name: str = ""
    source_url: str = ""
    attribution_text: str = ""
    servings: tuple[ExternalFoodServing, ...] = ()
    raw_payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_text(self.provider):
            raise ExternalFoodProviderError("provider is required.")
        if not _clean_text(self.external_food_id):
            raise ExternalFoodProviderError("external_food_id is required.")
        if not _clean_text(self.name):
            raise ExternalFoodProviderError("name is required.")
        object.__setattr__(self, "provider", _clean_text(self.provider))
        object.__setattr__(self, "external_food_id", _clean_text(self.external_food_id))
        object.__setattr__(self, "name", _clean_text(self.name))
        object.__setattr__(self, "brand_name", _clean_text(self.brand_name))
        object.__setattr__(self, "source_url", _clean_text(self.source_url))
        object.__setattr__(self, "attribution_text", _clean_text(self.attribution_text))
        object.__setattr__(self, "servings", tuple(self.servings or ()))


__all__ = [
    "ExternalFoodDetail",
    "ExternalFoodProviderConfigurationError",
    "ExternalFoodProviderError",
    "ExternalFoodSearchResult",
    "ExternalFoodServing",
]
