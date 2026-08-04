"""Unified Food Catalog search contracts and services.

This module searches master ``CatalogFood`` records and optional external
lookup providers without crossing the operational boundary. Results from
external providers remain references/lookup candidates; they are not converted
into curated ``CatalogFood`` rows or operational ``notas.Food`` records.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from food_catalog.application.external_providers.contracts import (
    ExternalFoodProviderError,
    ExternalFoodSearchResult,
)
from food_catalog.application.external_providers.references import (
    record_external_provider_fetch,
    upsert_external_food_reference_from_search_result,
)
from food_catalog.application.imports.normalization import normalize_food_name
from food_catalog.models import CatalogFood, ExternalProviderFetchLog

SOURCE_KIND_CATALOG = "catalog"
SOURCE_KIND_EXTERNAL = "external"
DEFAULT_CATALOG_SEARCH_LIMIT = 10
DEFAULT_EXTERNAL_SEARCH_LIMIT = 10
MAX_CATALOG_SEARCH_LIMIT = 50
MAX_EXTERNAL_SEARCH_LIMIT = 25


class ExternalSearchProvider(Protocol):
    """Minimal protocol required from lookup-only external providers."""

    provider_key: str

    def search(self, query: str, *, max_results: int = 10) -> tuple[ExternalFoodSearchResult, ...]:
        """Return normalized external lookup results."""


@dataclass(frozen=True)
class UnifiedFoodSearchItem:
    """One unified search item.

    ``source_kind='catalog'`` means the item is a curated master catalog row.
    ``source_kind='external'`` means the item is a provider lookup candidate and
    must not be used as operational food until an explicit later workflow
    re-fetches/curates/snapshots it.
    """

    source_kind: str
    display_name: str
    brand_name: str = ""
    source_label: str = ""
    catalog_food_id: int | None = None
    catalog_ref: str = ""
    external_reference_id: int | None = None
    provider: str = ""
    external_food_id: str = ""
    external_serving_id: str = ""
    description: str = ""
    source_url: str = ""
    attribution_text: str = ""
    data_quality_score: int | None = None
    is_solver_enabled: bool = False
    requires_external_refresh: bool = False

    @property
    def is_catalog_item(self) -> bool:
        return self.source_kind == SOURCE_KIND_CATALOG

    @property
    def is_external_item(self) -> bool:
        return self.source_kind == SOURCE_KIND_EXTERNAL


@dataclass(frozen=True)
class UnifiedFoodSearchResults:
    """Unified search response with catalog results first and external next."""

    query: str
    items: tuple[UnifiedFoodSearchItem, ...]
    catalog_count: int
    external_count: int
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExternalProviderSearchOutcome:
    """External provider search outcome.

    Errors are captured instead of leaking provider exceptions into UI/commands.
    """

    items: tuple[UnifiedFoodSearchItem, ...]
    errors: tuple[str, ...] = ()


def search_catalog_foods(
    query: str,
    *,
    limit: int = DEFAULT_CATALOG_SEARCH_LIMIT,
    include_unpublished: bool = False,
) -> tuple[UnifiedFoodSearchItem, ...]:
    """Search Food Catalog master rows for curators/product flows.

    This does not read ``notas.Food``. Operational food search remains owned by
    the operational app. Catalog results are returned only as master catalog
    candidates and must still go through explicit snapshot publication before
    becoming operational foods.
    """

    normalized_limit = _normalize_limit(limit, default=DEFAULT_CATALOG_SEARCH_LIMIT, maximum=MAX_CATALOG_SEARCH_LIMIT)
    search_text = query.strip()
    queryset = CatalogFood.objects.all()
    if not include_unpublished:
        queryset = queryset.filter(status=CatalogFood.STATUS_PUBLISHED)

    if search_text:
        normalized_query = normalize_food_name(search_text)
        by_display_name = queryset.filter(display_name__icontains=search_text)
        by_canonical_name = queryset.filter(canonical_name__icontains=normalized_query)
        by_brand_name = queryset.filter(brand_name__icontains=search_text)
        by_alias = queryset.filter(aliases__normalized_name__icontains=normalized_query)
        queryset = (by_display_name | by_canonical_name | by_brand_name | by_alias).distinct()

    queryset = queryset.order_by("display_name", "brand_name", "country")[:normalized_limit]
    return tuple(_catalog_food_to_search_item(catalog_food) for catalog_food in queryset)


def search_external_food_provider(
    provider: ExternalSearchProvider,
    query: str,
    *,
    limit: int = DEFAULT_EXTERNAL_SEARCH_LIMIT,
    record_references: bool = True,
) -> ExternalProviderSearchOutcome:
    """Search an external provider and optionally record reference metadata.

    When ``record_references`` is true, only provider identifiers, attribution,
    display metadata and payload hashes are persisted through
    ``ExternalFoodReference``. Nutrition payloads are never persisted here.
    """

    search_text = query.strip()
    if not search_text:
        return ExternalProviderSearchOutcome(items=(), errors=("query is required",))

    normalized_limit = _normalize_limit(limit, default=DEFAULT_EXTERNAL_SEARCH_LIMIT, maximum=MAX_EXTERNAL_SEARCH_LIMIT)
    try:
        provider_results = provider.search(search_text, max_results=normalized_limit)
    except ExternalFoodProviderError as exc:
        record_external_provider_fetch(
            provider=provider.provider_key,
            lookup_type=ExternalProviderFetchLog.LOOKUP_SEARCH,
            status=ExternalProviderFetchLog.STATUS_FAILED,
            query=search_text,
            error_message=str(exc),
        )
        return ExternalProviderSearchOutcome(items=(), errors=(str(exc),))

    record_external_provider_fetch(
        provider=provider.provider_key,
        lookup_type=ExternalProviderFetchLog.LOOKUP_SEARCH,
        status=ExternalProviderFetchLog.STATUS_SUCCESS,
        query=search_text,
        raw_payload={
            "result_count": len(provider_results),
            "external_food_ids": [result.external_food_id for result in provider_results],
        },
    )

    items: list[UnifiedFoodSearchItem] = []
    for result in provider_results:
        external_reference_id: int | None = None
        if record_references:
            recorded = upsert_external_food_reference_from_search_result(result)
            external_reference_id = recorded.reference.pk
        items.append(_external_result_to_search_item(result, external_reference_id=external_reference_id))

    return ExternalProviderSearchOutcome(items=tuple(items))


def search_unified_food_catalog(
    query: str,
    *,
    catalog_limit: int = DEFAULT_CATALOG_SEARCH_LIMIT,
    external_limit: int = DEFAULT_EXTERNAL_SEARCH_LIMIT,
    external_provider: ExternalSearchProvider | None = None,
    external_providers: Sequence[ExternalSearchProvider] | None = None,
    include_external: bool = False,
    record_external_references: bool = True,
) -> UnifiedFoodSearchResults:
    """Search local curated catalog first and optional external providers next."""

    catalog_items = search_catalog_foods(query, limit=catalog_limit)
    external_items: list[UnifiedFoodSearchItem] = []
    errors: list[str] = []

    if include_external:
        providers = _normalize_external_providers(
            external_provider=external_provider,
            external_providers=external_providers,
        )
        for provider in providers:
            outcome = search_external_food_provider(
                provider,
                query,
                limit=external_limit,
                record_references=record_external_references,
            )
            external_items.extend(outcome.items)
            errors.extend(outcome.errors)

    items = (*catalog_items, *external_items)
    return UnifiedFoodSearchResults(
        query=query.strip(),
        items=items,
        catalog_count=len(catalog_items),
        external_count=len(external_items),
        errors=tuple(errors),
    )


def _normalize_external_providers(
    *,
    external_provider: ExternalSearchProvider | None,
    external_providers: Sequence[ExternalSearchProvider] | None,
) -> tuple[ExternalSearchProvider, ...]:
    providers: list[ExternalSearchProvider] = []
    if external_provider is not None:
        providers.append(external_provider)
    if external_providers:
        providers.extend(provider for provider in external_providers if provider is not None)

    deduped: list[ExternalSearchProvider] = []
    seen_keys: set[str] = set()
    for provider in providers:
        key = getattr(provider, "provider_key", repr(provider))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(provider)
    return tuple(deduped)


def _catalog_food_to_search_item(catalog_food: CatalogFood) -> UnifiedFoodSearchItem:
    return UnifiedFoodSearchItem(
        source_kind=SOURCE_KIND_CATALOG,
        source_label="MyScoope Catalog",
        catalog_food_id=catalog_food.pk,
        catalog_ref=str(catalog_food.catalog_ref),
        display_name=catalog_food.display_name,
        brand_name=catalog_food.brand_name,
        data_quality_score=catalog_food.data_quality_score,
        is_solver_enabled=catalog_food.solver_enabled,
    )


def _external_result_to_search_item(
    result: ExternalFoodSearchResult,
    *,
    external_reference_id: int | None,
) -> UnifiedFoodSearchItem:
    return UnifiedFoodSearchItem(
        source_kind=SOURCE_KIND_EXTERNAL,
        source_label=result.provider,
        external_reference_id=external_reference_id,
        provider=result.provider,
        external_food_id=result.external_food_id,
        display_name=result.name,
        brand_name=result.brand_name,
        description=result.description,
        source_url=result.source_url,
        attribution_text=result.attribution_text,
        requires_external_refresh=True,
    )


def _normalize_limit(value: int, *, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return min(parsed, maximum)


__all__ = [
    "DEFAULT_CATALOG_SEARCH_LIMIT",
    "DEFAULT_EXTERNAL_SEARCH_LIMIT",
    "ExternalProviderSearchOutcome",
    "ExternalSearchProvider",
    "SOURCE_KIND_CATALOG",
    "SOURCE_KIND_EXTERNAL",
    "UnifiedFoodSearchItem",
    "UnifiedFoodSearchResults",
    "search_catalog_foods",
    "search_external_food_provider",
    "search_unified_food_catalog",
]
