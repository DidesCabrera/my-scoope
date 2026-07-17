"""FatSecret external provider client.

This module intentionally keeps FatSecret as an external lookup provider. It
returns normalized DTOs and does not create ``CatalogFood`` records, operational
``notas.Food`` records, or persistent nutrition snapshots by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

import requests
from requests import Response
from requests.auth import HTTPBasicAuth

from food_catalog.application.external_providers.contracts import (
    ExternalFoodDetail,
    ExternalFoodProviderConfigurationError,
    ExternalFoodProviderError,
    ExternalFoodSearchResult,
    ExternalFoodServing,
)
from food_catalog.application.imports.sources import SOURCE_FATSECRET


FATSECRET_ATTRIBUTION_TEXT = "Nutrition data provided by FatSecret."
DEFAULT_FATSECRET_TOKEN_URL = "https://oauth.fatsecret.com/connect/token"
DEFAULT_FATSECRET_API_BASE_URL = "https://platform.fatsecret.com/rest/server.api"


@dataclass(frozen=True)
class FatSecretProviderConfig:
    """Runtime configuration for the FatSecret provider."""

    client_id: str = ""
    client_secret: str = ""
    token_url: str = DEFAULT_FATSECRET_TOKEN_URL
    api_base_url: str = DEFAULT_FATSECRET_API_BASE_URL
    timeout_seconds: int = 15
    enabled: bool = False

    @property
    def is_configured(self) -> bool:
        return self.enabled and bool(self.client_id.strip()) and bool(self.client_secret.strip())


class FatSecretProvider:
    """Lookup-only FatSecret provider.

    The provider stores no response data internally except the in-memory access
    token for the current instance. Persistence/caching decisions must be made by
    a later application service that understands provider terms.
    """

    provider_key = SOURCE_FATSECRET
    attribution_text = FATSECRET_ATTRIBUTION_TEXT

    def __init__(self, config: FatSecretProviderConfig, *, session: requests.Session | None = None) -> None:
        self.config = config
        self.session = session or requests.Session()
        self._access_token = ""

    @classmethod
    def from_django_settings(cls, django_settings: Any, *, session: requests.Session | None = None) -> "FatSecretProvider":
        config = FatSecretProviderConfig(
            client_id=getattr(django_settings, "FOOD_CATALOG_FATSECRET_CLIENT_ID", ""),
            client_secret=getattr(django_settings, "FOOD_CATALOG_FATSECRET_CLIENT_SECRET", ""),
            token_url=getattr(django_settings, "FOOD_CATALOG_FATSECRET_TOKEN_URL", DEFAULT_FATSECRET_TOKEN_URL),
            api_base_url=getattr(
                django_settings,
                "FOOD_CATALOG_FATSECRET_API_BASE_URL",
                DEFAULT_FATSECRET_API_BASE_URL,
            ),
            timeout_seconds=int(getattr(django_settings, "FOOD_CATALOG_FATSECRET_TIMEOUT_SECONDS", 15)),
            enabled=bool(getattr(django_settings, "FOOD_CATALOG_FATSECRET_ENABLED", False)),
        )
        return cls(config, session=session)

    def search(self, query: str, *, max_results: int = 10, page_number: int = 0) -> tuple[ExternalFoodSearchResult, ...]:
        """Search FatSecret foods and return normalized lookup results."""

        query = query.strip()
        if not query:
            raise ExternalFoodProviderError("query is required.")
        payload = self._api_get(
            {
                "method": "foods.search.v3",
                "search_expression": query,
                "max_results": str(max_results),
                "page_number": str(page_number),
            }
        )
        foods = _extract_search_foods(payload)
        return tuple(self._map_search_result(food) for food in foods)

    def get_food(self, external_food_id: str) -> ExternalFoodDetail:
        """Return one FatSecret food detail by external food id."""

        external_food_id = external_food_id.strip()
        if not external_food_id:
            raise ExternalFoodProviderError("external_food_id is required.")
        payload = self._api_get({"method": "food.get.v4", "food_id": external_food_id})
        food_payload = payload.get("food", payload)
        if not isinstance(food_payload, Mapping):
            raise ExternalFoodProviderError("FatSecret detail response did not include a food payload.")
        return self._map_detail(food_payload)

    def get_serving(self, external_food_id: str, external_serving_id: str) -> ExternalFoodServing | None:
        """Return one serving from a FatSecret food detail, if present."""

        detail = self.get_food(external_food_id)
        external_serving_id = external_serving_id.strip()
        for serving in detail.servings:
            if serving.external_serving_id == external_serving_id:
                return serving
        return None

    def _ensure_configured(self) -> None:
        if not self.config.enabled:
            raise ExternalFoodProviderConfigurationError("FatSecret provider is disabled.")
        if not self.config.client_id.strip() or not self.config.client_secret.strip():
            raise ExternalFoodProviderConfigurationError("FatSecret client id and secret are required.")

    def _get_access_token(self) -> str:
        self._ensure_configured()
        if self._access_token:
            return self._access_token
        response = self.session.post(
            self.config.token_url,
            data={"grant_type": "client_credentials", "scope": "basic"},
            auth=HTTPBasicAuth(self.config.client_id, self.config.client_secret),
            timeout=self.config.timeout_seconds,
        )
        data = _decode_json_response(response, context="FatSecret token")
        token = str(data.get("access_token", "")).strip()
        if not token:
            raise ExternalFoodProviderError("FatSecret token response did not include access_token.")
        self._access_token = token
        return token

    def _api_get(self, params: dict[str, str]) -> Mapping[str, Any]:
        access_token = self._get_access_token()
        response = self.session.get(
            self.config.api_base_url,
            params={**params, "format": "json"},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=self.config.timeout_seconds,
        )
        return _decode_json_response(response, context="FatSecret API")

    def _map_search_result(self, payload: Mapping[str, Any]) -> ExternalFoodSearchResult:
        return ExternalFoodSearchResult(
            provider=self.provider_key,
            external_food_id=str(payload.get("food_id", "")),
            name=str(payload.get("food_name", "")),
            brand_name=str(payload.get("brand_name", "")),
            description=str(payload.get("food_description", "")),
            source_url=str(payload.get("food_url", "")),
            attribution_text=self.attribution_text,
            raw_payload=dict(payload),
        )

    def _map_detail(self, payload: Mapping[str, Any]) -> ExternalFoodDetail:
        external_food_id = str(payload.get("food_id", ""))
        servings_payload = _as_list(_nested(payload, "servings", "serving"))
        servings = tuple(self._map_serving(external_food_id, serving) for serving in servings_payload)
        return ExternalFoodDetail(
            provider=self.provider_key,
            external_food_id=external_food_id,
            name=str(payload.get("food_name", "")),
            brand_name=str(payload.get("brand_name", "")),
            source_url=str(payload.get("food_url", "")),
            attribution_text=self.attribution_text,
            servings=servings,
            raw_payload=dict(payload),
        )

    def _map_serving(self, external_food_id: str, payload: Mapping[str, Any]) -> ExternalFoodServing:
        metric_unit = str(payload.get("metric_serving_unit", ""))
        metric_amount = _decimal_or_none(payload.get("metric_serving_amount"))
        grams = metric_amount if metric_unit.lower() in {"g", "gram", "grams"} else None
        return ExternalFoodServing(
            provider=self.provider_key,
            external_food_id=external_food_id,
            external_serving_id=str(payload.get("serving_id", "")),
            serving_description=str(payload.get("serving_description", "")),
            metric_serving_amount=metric_amount,
            metric_serving_unit=metric_unit,
            grams=grams,
            calories_kcal=payload.get("calories"),
            protein_g=payload.get("protein"),
            carbs_g=payload.get("carbohydrate"),
            fat_g=payload.get("fat"),
            raw_payload=dict(payload),
        )


def _decode_json_response(response: Response, *, context: str) -> Mapping[str, Any]:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise ExternalFoodProviderError(f"{context} request failed: {response.status_code}") from exc
    try:
        data = response.json()
    except ValueError as exc:
        raise ExternalFoodProviderError(f"{context} response was not valid JSON.") from exc
    if not isinstance(data, Mapping):
        raise ExternalFoodProviderError(f"{context} response must be a JSON object.")
    return data


def _nested(payload: Mapping[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _as_list(value: Any) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, Mapping)]
    return []


def _extract_search_foods(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Extract search results from current v3 and legacy FatSecret envelopes."""

    candidates = (
        _nested(payload, "foods_search", "results", "food"),
        _nested(payload, "foods_search", "food"),
        _nested(payload, "foods", "food"),
    )
    for candidate in candidates:
        if candidate is not None:
            return _as_list(candidate)

    total_results = _nested(payload, "foods_search", "total_results")
    try:
        has_results = int(str(total_results or "0")) > 0
    except ValueError:
        has_results = False
    if has_results:
        raise ExternalFoodProviderError(
            "FatSecret search response reported results but used an unsupported payload shape."
        )
    return []


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ExternalFoodProviderError(f"Invalid FatSecret numeric value: {value!r}") from exc


__all__ = [
    "DEFAULT_FATSECRET_API_BASE_URL",
    "DEFAULT_FATSECRET_TOKEN_URL",
    "FATSECRET_ATTRIBUTION_TEXT",
    "FatSecretProvider",
    "FatSecretProviderConfig",
]
