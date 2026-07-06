from decimal import Decimal

from django.test import SimpleTestCase

from food_catalog.application.external_providers.contracts import (
    ExternalFoodDetail,
    ExternalFoodProviderError,
    ExternalFoodSearchResult,
    ExternalFoodServing,
)


class ExternalFoodProviderContractTests(SimpleTestCase):
    def test_search_result_requires_provider_external_id_and_name(self):
        with self.assertRaises(ExternalFoodProviderError):
            ExternalFoodSearchResult(provider="fatsecret", external_food_id="", name="Avena")

    def test_serving_normalizes_numeric_values(self):
        serving = ExternalFoodServing(
            provider="fatsecret",
            external_food_id="123",
            external_serving_id="456",
            metric_serving_amount="100.0",
            metric_serving_unit="g",
            grams="100.0",
            calories_kcal="389",
            protein_g="16.9",
            carbs_g="66.3",
            fat_g="6.9",
        )

        self.assertEqual(serving.grams, Decimal("100.0"))
        self.assertEqual(serving.protein_g, Decimal("16.9"))

    def test_detail_keeps_servings_immutable_tuple(self):
        serving = ExternalFoodServing(provider="fatsecret", external_food_id="123")
        detail = ExternalFoodDetail(
            provider="fatsecret",
            external_food_id="123",
            name="Oats",
            servings=[serving],
        )

        self.assertEqual(detail.servings, (serving,))
