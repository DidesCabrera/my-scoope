from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from food_catalog.application.external_providers.contracts import (
    ExternalFoodProviderConfigurationError,
    ExternalFoodProviderError,
)
from food_catalog.infrastructure.external_providers.fatsecret import (
    FATSECRET_ATTRIBUTION_TEXT,
    FatSecretProvider,
    FatSecretProviderConfig,
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
        self.post_calls = []
        self.get_calls = []
        self.token_payload = {"access_token": "token-123"}
        self.get_payload = {}

    def post(self, url, *, data, auth, timeout):
        self.post_calls.append({"url": url, "data": data, "auth": auth, "timeout": timeout})
        return FakeResponse(self.token_payload)

    def get(self, url, *, params, headers, timeout):
        self.get_calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return FakeResponse(self.get_payload)


class FatSecretProviderTests(SimpleTestCase):
    def test_provider_requires_enabled_credentials(self):
        provider = FatSecretProvider(FatSecretProviderConfig(enabled=False))

        with self.assertRaises(ExternalFoodProviderConfigurationError):
            provider.search("avena")

    def test_search_maps_v3_fatsecret_results_without_persisting(self):
        session = FakeSession()
        session.get_payload = {
            "foods_search": {
                "total_results": "1",
                "results": {
                    "food": [
                        {
                            "food_id": "123",
                            "food_name": "Avena",
                            "brand_name": "",
                            "food_description": "100 g - 389 kcal",
                            "food_url": "https://example.test/food/123",
                        }
                    ]
                },
            }
        }
        provider = FatSecretProvider(
            FatSecretProviderConfig(client_id="client", client_secret="secret", enabled=True),
            session=session,
        )

        results = provider.search("avena", max_results=5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].provider, "fatsecret")
        self.assertEqual(results[0].external_food_id, "123")
        self.assertEqual(results[0].name, "Avena")
        self.assertEqual(results[0].attribution_text, FATSECRET_ATTRIBUTION_TEXT)
        self.assertEqual(session.get_calls[0]["params"]["method"], "foods.search.v3")
        self.assertEqual(session.get_calls[0]["headers"]["Authorization"], "Bearer token-123")

    def test_search_keeps_legacy_response_compatibility(self):
        session = FakeSession()
        session.get_payload = {
            "foods": {
                "food": {
                    "food_id": "123",
                    "food_name": "Avena",
                }
            }
        }
        provider = FatSecretProvider(
            FatSecretProviderConfig(client_id="client", client_secret="secret", enabled=True),
            session=session,
        )

        results = provider.search("avena")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].external_food_id, "123")

    def test_search_raises_when_nonempty_v3_response_shape_is_unknown(self):
        session = FakeSession()
        session.get_payload = {
            "foods_search": {
                "total_results": "1",
                "unexpected_results": {"food": {"food_id": "123"}},
            }
        }
        provider = FatSecretProvider(
            FatSecretProviderConfig(client_id="client", client_secret="secret", enabled=True),
            session=session,
        )

        with self.assertRaisesMessage(ExternalFoodProviderError, "unsupported payload shape"):
            provider.search("avena")

    def test_search_allows_a_genuine_empty_v3_result(self):
        session = FakeSession()
        session.get_payload = {"foods_search": {"total_results": "0"}}
        provider = FatSecretProvider(
            FatSecretProviderConfig(client_id="client", client_secret="secret", enabled=True),
            session=session,
        )

        self.assertEqual(provider.search("not-a-food"), ())

    def test_detail_maps_servings_and_grams(self):
        session = FakeSession()
        session.get_payload = {
            "food": {
                "food_id": "123",
                "food_name": "Avena",
                "food_url": "https://example.test/food/123",
                "servings": {
                    "serving": {
                        "serving_id": "456",
                        "serving_description": "100 g",
                        "metric_serving_amount": "100.000",
                        "metric_serving_unit": "g",
                        "calories": "389",
                        "protein": "16.9",
                        "carbohydrate": "66.3",
                        "fat": "6.9",
                    }
                },
            }
        }
        provider = FatSecretProvider(
            FatSecretProviderConfig(client_id="client", client_secret="secret", enabled=True),
            session=session,
        )

        detail = provider.get_food("123")

        self.assertEqual(detail.name, "Avena")
        self.assertEqual(len(detail.servings), 1)
        self.assertEqual(detail.servings[0].external_serving_id, "456")
        self.assertEqual(detail.servings[0].grams, Decimal("100.000"))
        self.assertEqual(detail.servings[0].protein_g, Decimal("16.9"))

    def test_get_serving_returns_matching_serving(self):
        session = FakeSession()
        session.get_payload = {
            "food": {
                "food_id": "123",
                "food_name": "Avena",
                "servings": {
                    "serving": [
                        {"serving_id": "a", "serving_description": "1 cup"},
                        {"serving_id": "b", "serving_description": "100 g"},
                    ]
                },
            }
        }
        provider = FatSecretProvider(
            FatSecretProviderConfig(client_id="client", client_secret="secret", enabled=True),
            session=session,
        )

        serving = provider.get_serving("123", "b")

        self.assertIsNotNone(serving)
        self.assertEqual(serving.external_serving_id, "b")

    def test_bad_http_response_raises_provider_error(self):
        session = FakeSession()
        session.get_payload = {"error": "bad"}
        session.get = lambda *args, **kwargs: FakeResponse({"error": "bad"}, status_code=500)
        provider = FatSecretProvider(
            FatSecretProviderConfig(client_id="client", client_secret="secret", enabled=True),
            session=session,
        )

        with self.assertRaises(ExternalFoodProviderError):
            provider.search("avena")

    def test_api_error_inside_successful_http_response_is_not_an_empty_search(self):
        session = FakeSession()
        session.get_payload = {
            "error": {
                "code": 21,
                "message": "Invalid IP address detected.",
            }
        }
        provider = FatSecretProvider(
            FatSecretProviderConfig(client_id="client", client_secret="secret", enabled=True),
            session=session,
        )

        with self.assertRaisesMessage(
            ExternalFoodProviderError,
            "FatSecret API error 21: Invalid IP address detected.",
        ):
            provider.search("avena")

    @override_settings(
        FOOD_CATALOG_FATSECRET_ENABLED=True,
        FOOD_CATALOG_FATSECRET_CLIENT_ID="client",
        FOOD_CATALOG_FATSECRET_CLIENT_SECRET="secret",
        FOOD_CATALOG_FATSECRET_TIMEOUT_SECONDS=9,
    )
    def test_from_django_settings_builds_config(self):
        from django.conf import settings

        provider = FatSecretProvider.from_django_settings(settings, session=FakeSession())

        self.assertTrue(provider.config.is_configured)
        self.assertEqual(provider.config.timeout_seconds, 9)
