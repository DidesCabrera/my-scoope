from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from food_catalog.application.external_providers.contracts import (
    ExternalFoodProviderConfigurationError,
    ExternalFoodProviderError,
)
from food_catalog.infrastructure.external_providers.open_food_facts import (
    OPEN_FOOD_FACTS_ATTRIBUTION_TEXT,
    OpenFoodFactsProvider,
    OpenFoodFactsProviderConfig,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError("boom")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.get_calls = []
        self.get_payload = {}

    def get(self, url, *, params, headers, timeout):
        self.get_calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return FakeResponse(self.get_payload)


class OpenFoodFactsProviderTests(SimpleTestCase):
    def test_provider_requires_enabled_config(self):
        provider = OpenFoodFactsProvider(OpenFoodFactsProviderConfig(enabled=False))

        with self.assertRaises(ExternalFoodProviderConfigurationError):
            provider.search("avena")

    def test_search_maps_open_food_facts_results_without_persisting(self):
        session = FakeSession()
        session.get_payload = {
            "products": [
                {
                    "code": "7801234567890",
                    "product_name": "Avena integral",
                    "brands": "Marca Test",
                    "url": "https://world.openfoodfacts.org/product/7801234567890",
                    "nutriments": {
                        "energy-kcal_100g": 389,
                        "proteins_100g": 13.5,
                        "carbohydrates_100g": 68,
                        "fat_100g": 7,
                    },
                }
            ]
        }
        provider = OpenFoodFactsProvider(OpenFoodFactsProviderConfig(enabled=True), session=session)

        results = provider.search("avena", max_results=5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].provider, "open_food_facts")
        self.assertEqual(results[0].external_food_id, "7801234567890")
        self.assertEqual(results[0].name, "Avena integral")
        self.assertEqual(results[0].brand_name, "Marca Test")
        self.assertEqual(results[0].attribution_text, OPEN_FOOD_FACTS_ATTRIBUTION_TEXT)
        self.assertEqual(session.get_calls[0]["params"]["search_terms"], "avena")
        self.assertEqual(session.get_calls[0]["headers"]["User-Agent"], provider.config.user_agent)

    def test_detail_maps_per_100g_and_serving(self):
        session = FakeSession()
        session.get_payload = {
            "status": 1,
            "product": {
                "code": "7801234567890",
                "product_name_es": "Yogur natural",
                "brands": "Marca Test",
                "url": "https://world.openfoodfacts.org/product/7801234567890",
                "serving_size": "125 g",
                "serving_quantity": "125",
                "nutriments": {
                    "energy-kcal_100g": "60",
                    "proteins_100g": "5.0",
                    "carbohydrates_100g": "7.0",
                    "fat_100g": "2.0",
                },
            },
        }
        provider = OpenFoodFactsProvider(OpenFoodFactsProviderConfig(enabled=True), session=session)

        detail = provider.get_food("7801234567890")

        self.assertEqual(detail.name, "Yogur natural")
        self.assertEqual(len(detail.servings), 2)
        self.assertEqual(detail.servings[0].external_serving_id, "per_100g")
        self.assertEqual(detail.servings[0].grams, Decimal("100"))
        self.assertEqual(detail.servings[0].protein_g, Decimal("5.0"))
        self.assertEqual(detail.servings[1].external_serving_id, "serving")
        self.assertEqual(detail.servings[1].grams, Decimal("125"))
        self.assertEqual(detail.servings[1].calories_kcal, Decimal("75"))

    def test_get_serving_returns_matching_serving(self):
        session = FakeSession()
        session.get_payload = {
            "status": 1,
            "product": {
                "code": "7801234567890",
                "product_name": "Yogur natural",
                "serving_quantity": "125",
                "nutriments": {"energy-kcal_100g": "60"},
            },
        }
        provider = OpenFoodFactsProvider(OpenFoodFactsProviderConfig(enabled=True), session=session)

        serving = provider.get_serving("7801234567890", "serving")

        self.assertIsNotNone(serving)
        self.assertEqual(serving.external_serving_id, "serving")

    def test_not_found_detail_raises_provider_error(self):
        session = FakeSession()
        session.get_payload = {"status": 0}
        provider = OpenFoodFactsProvider(OpenFoodFactsProviderConfig(enabled=True), session=session)

        with self.assertRaises(ExternalFoodProviderError):
            provider.get_food("missing")

    def test_bad_http_response_raises_provider_error(self):
        session = FakeSession()
        session.get = lambda *args, **kwargs: FakeResponse({"error": "bad"}, status_code=500)
        provider = OpenFoodFactsProvider(OpenFoodFactsProviderConfig(enabled=True), session=session)

        with self.assertRaises(ExternalFoodProviderError):
            provider.search("avena")

    @override_settings(
        FOOD_CATALOG_OPEN_FOOD_FACTS_ENABLED=True,
        FOOD_CATALOG_OPEN_FOOD_FACTS_API_BASE_URL="https://off.example.test",
        FOOD_CATALOG_OPEN_FOOD_FACTS_TIMEOUT_SECONDS=7,
        FOOD_CATALOG_OPEN_FOOD_FACTS_USER_AGENT="MyScoope Tests/1.0",
    )
    def test_from_django_settings_builds_config(self):
        from django.conf import settings

        provider = OpenFoodFactsProvider.from_django_settings(settings, session=FakeSession())

        self.assertTrue(provider.config.is_configured)
        self.assertEqual(provider.config.api_base_url, "https://off.example.test")
        self.assertEqual(provider.config.timeout_seconds, 7)
        self.assertEqual(provider.config.user_agent, "MyScoope Tests/1.0")
