"""Open Food Facts external provider client.

This module keeps Open Food Facts as an external lookup/open-data provider. It
returns normalized DTOs and does not create ``CatalogFood`` records,
operational ``notas.Food`` records, or persistent nutrition snapshots by
itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

import requests

from food_catalog.application.external_providers.contracts import (
    ExternalFoodDetail,
    ExternalFoodProviderConfigurationError,
    ExternalFoodProviderError,
    ExternalFoodSearchResult,
    ExternalFoodServing,
)
from food_catalog.application.imports.sources import SOURCE_OPEN_FOOD_FACTS


OPEN_FOOD_FACTS_ATTRIBUTION_TEXT = "Food data from Open Food Facts."
DEFAULT_OPEN_FOOD_FACTS_API_BASE_URL = "https://world.openfoodfacts.org"
DEFAULT_OPEN_FOOD_FACTS_USER_AGENT = "MyScoope FoodCatalog/1.0 (contact: support@myscoope.com)"


@dataclass(frozen=True)
class OpenFoodFactsProviderConfig:
    """Runtime configuration for the Open Food Facts provider."""

    api_base_url: str = DEFAULT_OPEN_FOOD_FACTS_API_BASE_URL
    timeout_seconds: int = 15
    enabled: bool = False
    user_agent: str = DEFAULT_OPEN_FOOD_FACTS_USER_AGENT

    @property
    def is_configured(self) -> bool:
        return self.enabled and bool(self.api_base_url.strip())


class OpenFoodFactsProvider:
    """Lookup-only Open Food Facts provider.

    The provider performs live HTTP lookups and returns normalized DTOs. Any
    persistence must happen through explicit Food Catalog application services,
    such as external references or curation candidates.
    """

    provider_key = SOURCE_OPEN_FOOD_FACTS
    attribution_text = OPEN_FOOD_FACTS_ATTRIBUTION_TEXT

    def __init__(self, config: OpenFoodFactsProviderConfig, *, session: requests.Session | None = None) -> None:
        self.config = config
        self.session = session or requests.Session()

    @classmethod
    def from_django_settings(
        cls,
        django_settings: Any,
        *,
        session: requests.Session | None = None,
    ) -> "OpenFoodFactsProvider":
        config = OpenFoodFactsProviderConfig(
            api_base_url=getattr(
                django_settings,
                "FOOD_CATALOG_OPEN_FOOD_FACTS_API_BASE_URL",
                DEFAULT_OPEN_FOOD_FACTS_API_BASE_URL,
            ),
            timeout_seconds=int(getattr(django_settings, "FOOD_CATALOG_OPEN_FOOD_FACTS_TIMEOUT_SECONDS", 15)),
            enabled=bool(getattr(django_settings, "FOOD_CATALOG_OPEN_FOOD_FACTS_ENABLED", False)),
            user_agent=getattr(
                django_settings,
                "FOOD_CATALOG_OPEN_FOOD_FACTS_USER_AGENT",
                DEFAULT_OPEN_FOOD_FACTS_USER_AGENT,
            ),
        )
        return cls(config, session=session)

    def search(self, query: str, *, max_results: int = 10) -> tuple[ExternalFoodSearchResult, ...]:
        """Search Open Food Facts products and return normalized lookup results."""

        query = query.strip()
        if not query:
            raise ExternalFoodProviderError("query is required.")
        payload = self._get(
            "/cgi/search.pl",
            params={
                "search_terms": query,
                "search_simple": "1",
                "action": "process",
                "json": "1",
                "page_size": str(max_results),
                "fields": "code,product_name,product_name_es,brands,url,nutriments,serving_size,serving_quantity",
            },
        )
        products = payload.get("products") or []
        if not isinstance(products, list):
            raise ExternalFoodProviderError("Open Food Facts search returned an invalid products payload.")

        results: list[ExternalFoodSearchResult] = []
        for product in products:
            mapped = self._map_search_result(product)
            if mapped is not None:
                results.append(mapped)
        return tuple(results)

    def get_food(self, external_food_id: str) -> ExternalFoodDetail:
        """Return one Open Food Facts product detail by barcode/code."""

        code = external_food_id.strip()
        if not code:
            raise ExternalFoodProviderError("external_food_id is required.")
        payload = self._get(
            f"/api/v2/product/{code}.json",
            params={
                "fields": "code,product_name,product_name_es,brands,url,nutriments,serving_size,serving_quantity,serving_quantity_unit",
            },
        )
        if payload.get("status") == 0:
            raise ExternalFoodProviderError(f"Open Food Facts product not found: {code}")
        product = payload.get("product") or {}
        if not isinstance(product, Mapping):
            raise ExternalFoodProviderError("Open Food Facts detail returned an invalid product payload.")
        return self._map_detail(product, raw_payload=payload)

    def get_serving(self, external_food_id: str, external_serving_id: str | None = None) -> ExternalFoodServing | None:
        """Return a normalized OFF serving by id, usually ``per_100g`` or ``serving``."""

        detail = self.get_food(external_food_id)
        requested = (external_serving_id or "").strip()
        if not requested:
            return detail.servings[0] if detail.servings else None
        for serving in detail.servings:
            if serving.external_serving_id == requested:
                return serving
        return None

    def _get(self, path: str, *, params: Mapping[str, str]) -> Mapping[str, Any]:
        if not self.config.is_configured:
            raise ExternalFoodProviderConfigurationError("Open Food Facts provider is disabled or misconfigured.")
        url = f"{self.config.api_base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            response = self.session.get(
                url,
                params=params,
                headers={"User-Agent": self.config.user_agent},
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise ExternalFoodProviderError(f"Open Food Facts HTTP request failed: {exc}") from exc
        except ValueError as exc:
            raise ExternalFoodProviderError("Open Food Facts returned invalid JSON.") from exc
        if not isinstance(payload, Mapping):
            raise ExternalFoodProviderError("Open Food Facts returned a non-object JSON payload.")
        return payload

    def _map_search_result(self, product: Mapping[str, Any]) -> ExternalFoodSearchResult | None:
        code = str(product.get("code") or "").strip()
        name = _product_name(product)
        if not code or not name:
            return None
        return ExternalFoodSearchResult(
            provider=self.provider_key,
            external_food_id=code,
            name=name,
            brand_name=_brand_name(product),
            description=_search_description(product),
            source_url=str(product.get("url") or "").strip(),
            attribution_text=self.attribution_text,
            raw_payload=dict(product),
        )

    def _map_detail(self, product: Mapping[str, Any], *, raw_payload: Mapping[str, Any]) -> ExternalFoodDetail:
        code = str(product.get("code") or "").strip()
        name = _product_name(product)
        if not code or not name:
            raise ExternalFoodProviderError("Open Food Facts detail requires code and product name.")
        return ExternalFoodDetail(
            provider=self.provider_key,
            external_food_id=code,
            name=name,
            brand_name=_brand_name(product),
            source_url=str(product.get("url") or "").strip(),
            attribution_text=self.attribution_text,
            servings=_map_servings(product),
            raw_payload=raw_payload,
        )


def _product_name(product: Mapping[str, Any]) -> str:
    return str(product.get("product_name_es") or product.get("product_name") or "").strip()


def _brand_name(product: Mapping[str, Any]) -> str:
    brands = product.get("brands")
    if isinstance(brands, list):
        return ", ".join(str(brand).strip() for brand in brands if str(brand).strip())
    return str(brands or "").strip()


def _search_description(product: Mapping[str, Any]) -> str:
    nutriments = product.get("nutriments") or {}
    if not isinstance(nutriments, Mapping):
        return str(product.get("serving_size") or "").strip()
    kcal = nutriments.get("energy-kcal_100g")
    protein = nutriments.get("proteins_100g")
    carbs = nutriments.get("carbohydrates_100g")
    fat = nutriments.get("fat_100g")
    fragments = []
    if kcal not in (None, ""):
        fragments.append(f"{kcal} kcal/100g")
    macro_fragments = []
    if protein not in (None, ""):
        macro_fragments.append(f"P {protein}g")
    if carbs not in (None, ""):
        macro_fragments.append(f"C {carbs}g")
    if fat not in (None, ""):
        macro_fragments.append(f"F {fat}g")
    if macro_fragments:
        fragments.append(" · ".join(macro_fragments))
    return " · ".join(fragments)


def _map_servings(product: Mapping[str, Any]) -> tuple[ExternalFoodServing, ...]:
    nutriments = product.get("nutriments") or {}
    if not isinstance(nutriments, Mapping):
        nutriments = {}

    servings = [
        ExternalFoodServing(
            provider=SOURCE_OPEN_FOOD_FACTS,
            external_food_id=str(product.get("code") or "").strip(),
            external_serving_id="per_100g",
            serving_description="100 g",
            metric_serving_amount=Decimal("100"),
            metric_serving_unit="g",
            grams=Decimal("100"),
            calories_kcal=_decimal_or_none(nutriments.get("energy-kcal_100g")),
            protein_g=_decimal_or_none(nutriments.get("proteins_100g")),
            carbs_g=_decimal_or_none(nutriments.get("carbohydrates_100g")),
            fat_g=_decimal_or_none(nutriments.get("fat_100g")),
            raw_payload={"nutriments": dict(nutriments), "basis": "per_100g"},
        )
    ]

    serving_quantity = _decimal_or_none(product.get("serving_quantity"))
    if serving_quantity is not None and serving_quantity > 0:
        servings.append(
            ExternalFoodServing(
                provider=SOURCE_OPEN_FOOD_FACTS,
                external_food_id=str(product.get("code") or "").strip(),
                external_serving_id="serving",
                serving_description=str(product.get("serving_size") or f"{serving_quantity} g").strip(),
                metric_serving_amount=serving_quantity,
                metric_serving_unit=str(product.get("serving_quantity_unit") or "g").strip() or "g",
                grams=serving_quantity,
                calories_kcal=_scale_per_100g(nutriments.get("energy-kcal_100g"), serving_quantity),
                protein_g=_scale_per_100g(nutriments.get("proteins_100g"), serving_quantity),
                carbs_g=_scale_per_100g(nutriments.get("carbohydrates_100g"), serving_quantity),
                fat_g=_scale_per_100g(nutriments.get("fat_100g"), serving_quantity),
                raw_payload={"nutriments": dict(nutriments), "basis": "serving"},
            )
        )
    return tuple(servings)


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None


def _scale_per_100g(value: Any, grams: Decimal) -> Decimal | None:
    parsed = _decimal_or_none(value)
    if parsed is None:
        return None
    return (parsed * grams) / Decimal("100")


__all__ = [
    "DEFAULT_OPEN_FOOD_FACTS_API_BASE_URL",
    "DEFAULT_OPEN_FOOD_FACTS_USER_AGENT",
    "OPEN_FOOD_FACTS_ATTRIBUTION_TEXT",
    "OpenFoodFactsProvider",
    "OpenFoodFactsProviderConfig",
]
