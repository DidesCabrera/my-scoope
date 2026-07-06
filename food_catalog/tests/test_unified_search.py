from decimal import Decimal

from django.test import TestCase

from food_catalog.application.external_providers.contracts import (
    ExternalFoodProviderError,
    ExternalFoodSearchResult,
)
from food_catalog.application.unified_search import (
    SOURCE_KIND_CATALOG,
    SOURCE_KIND_EXTERNAL,
    search_catalog_foods,
    search_external_food_provider,
    search_unified_food_catalog,
)
from food_catalog.models import CatalogFood, ExternalFoodReference, ExternalProviderFetchLog


class FakeExternalProvider:
    provider_key = "fatsecret"

    def __init__(self, *, raises: Exception | None = None):
        self.raises = raises
        self.calls = []

    def search(self, query: str, *, max_results: int = 10):
        self.calls.append({"query": query, "max_results": max_results})
        if self.raises:
            raise self.raises
        return (
            ExternalFoodSearchResult(
                provider="fatsecret",
                external_food_id="fs-1",
                name="Avena FatSecret",
                brand_name="",
                description="100 g - 389 kcal",
                source_url="https://example.test/foods/fs-1",
                attribution_text="Nutrition data provided by FatSecret.",
                raw_payload={"food_id": "fs-1", "food_name": "Avena FatSecret"},
            ),
        )


class FakeOpenFoodFactsProvider(FakeExternalProvider):
    provider_key = "open_food_facts"

    def search(self, query: str, *, max_results: int = 10):
        self.calls.append({"query": query, "max_results": max_results})
        if self.raises:
            raise self.raises
        return (
            ExternalFoodSearchResult(
                provider="open_food_facts",
                external_food_id="off-1",
                name="Avena Open Food Facts",
                brand_name="Marca OFF",
                description="389 kcal/100g",
                source_url="https://world.openfoodfacts.org/product/off-1",
                attribution_text="Food data from Open Food Facts.",
                raw_payload={"code": "off-1", "product_name": "Avena Open Food Facts"},
            ),
        )


class UnifiedFoodSearchTests(TestCase):
    def setUp(self):
        self.published = CatalogFood.objects.create(
            display_name="Avena tradicional",
            canonical_name="avena tradicional",
            food_group="cereals",
            food_subgroup="oats",
            protein_g_per_100g=Decimal("13.500"),
            carbs_g_per_100g=Decimal("68.000"),
            fat_g_per_100g=Decimal("7.000"),
            calories_kcal_per_100g=Decimal("389.000"),
            status=CatalogFood.STATUS_PUBLISHED,
            source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
            data_quality_score=95,
            solver_enabled=True,
        )
        CatalogFood.objects.create(
            display_name="Avena pendiente",
            canonical_name="avena pendiente",
            food_group="cereals",
            protein_g_per_100g=Decimal("10.000"),
            carbs_g_per_100g=Decimal("60.000"),
            fat_g_per_100g=Decimal("6.000"),
            status=CatalogFood.STATUS_PENDING_REVIEW,
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            data_quality_score=50,
        )

    def test_search_catalog_foods_returns_only_published_by_default(self):
        results = search_catalog_foods("avena")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_kind, SOURCE_KIND_CATALOG)
        self.assertEqual(results[0].catalog_food_id, self.published.pk)
        self.assertEqual(results[0].source_label, "MyScoope Catalog")
        self.assertTrue(results[0].is_solver_enabled)

    def test_search_catalog_foods_can_include_unpublished_for_curation(self):
        results = search_catalog_foods("avena", include_unpublished=True)

        self.assertEqual(len(results), 2)

    def test_external_provider_search_records_reference_and_fetch_log(self):
        outcome = search_external_food_provider(FakeExternalProvider(), "avena", record_references=True)

        self.assertEqual(outcome.errors, ())
        self.assertEqual(len(outcome.items), 1)
        item = outcome.items[0]
        self.assertEqual(item.source_kind, SOURCE_KIND_EXTERNAL)
        self.assertEqual(item.external_reference_id, ExternalFoodReference.objects.get().pk)
        self.assertTrue(item.requires_external_refresh)
        self.assertEqual(ExternalProviderFetchLog.objects.count(), 1)
        self.assertEqual(ExternalProviderFetchLog.objects.get().status, ExternalProviderFetchLog.STATUS_SUCCESS)

    def test_external_provider_search_can_skip_reference_recording(self):
        outcome = search_external_food_provider(FakeExternalProvider(), "avena", record_references=False)

        self.assertEqual(len(outcome.items), 1)
        self.assertIsNone(outcome.items[0].external_reference_id)
        self.assertEqual(ExternalFoodReference.objects.count(), 0)
        self.assertEqual(ExternalProviderFetchLog.objects.count(), 1)

    def test_external_provider_error_is_logged_without_raising(self):
        outcome = search_external_food_provider(
            FakeExternalProvider(raises=ExternalFoodProviderError("provider unavailable")),
            "avena",
        )

        self.assertEqual(outcome.items, ())
        self.assertEqual(outcome.errors, ("provider unavailable",))
        self.assertEqual(ExternalProviderFetchLog.objects.count(), 1)
        self.assertEqual(ExternalProviderFetchLog.objects.get().status, ExternalProviderFetchLog.STATUS_FAILED)

    def test_unified_search_orders_catalog_before_external(self):
        results = search_unified_food_catalog(
            "avena",
            external_provider=FakeExternalProvider(),
            include_external=True,
            record_external_references=True,
        )

        self.assertEqual(results.catalog_count, 1)
        self.assertEqual(results.external_count, 1)
        self.assertEqual(results.items[0].source_kind, SOURCE_KIND_CATALOG)
        self.assertEqual(results.items[1].source_kind, SOURCE_KIND_EXTERNAL)
        self.assertEqual(ExternalFoodReference.objects.count(), 1)

    def test_unified_search_does_not_query_external_unless_requested(self):
        provider = FakeExternalProvider()

        results = search_unified_food_catalog("avena", external_provider=provider, include_external=False)

        self.assertEqual(results.catalog_count, 1)
        self.assertEqual(results.external_count, 0)
        self.assertEqual(provider.calls, [])
        self.assertEqual(ExternalProviderFetchLog.objects.count(), 0)
    def test_unified_search_can_query_multiple_external_providers(self):
        fatsecret = FakeExternalProvider()
        open_food_facts = FakeOpenFoodFactsProvider()

        results = search_unified_food_catalog(
            "avena",
            external_providers=[fatsecret, open_food_facts],
            include_external=True,
            record_external_references=True,
        )

        self.assertEqual(results.catalog_count, 1)
        self.assertEqual(results.external_count, 2)
        self.assertEqual(results.items[0].source_kind, SOURCE_KIND_CATALOG)
        self.assertEqual(results.items[1].provider, "fatsecret")
        self.assertEqual(results.items[2].provider, "open_food_facts")
        self.assertEqual(ExternalFoodReference.objects.count(), 2)
        self.assertEqual(ExternalProviderFetchLog.objects.count(), 2)
