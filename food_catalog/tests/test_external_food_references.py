from datetime import UTC, datetime, timedelta

from django.test import TestCase

from food_catalog.application.external_providers.contracts import (
    ExternalFoodDetail,
    ExternalFoodSearchResult,
    ExternalFoodServing,
)
from food_catalog.application.external_providers.references import (
    EXTERNAL_REFERENCE_REFRESH_HOURS,
    external_reference_expires_at,
    hash_external_payload,
    record_external_provider_fetch,
    upsert_external_food_reference_from_detail,
    upsert_external_food_reference_from_search_result,
)
from food_catalog.models import ExternalFoodReference, ExternalProviderFetchLog


class ExternalFoodReferenceTests(TestCase):
    def test_external_reference_expires_at_defaults_to_24_hours(self):
        now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)

        expires_at = external_reference_expires_at(now=now)

        self.assertEqual(expires_at, now + timedelta(hours=EXTERNAL_REFERENCE_REFRESH_HOURS))

    def test_hash_external_payload_is_stable_without_storing_raw_payload(self):
        first = hash_external_payload({"b": 2, "a": 1})
        second = hash_external_payload({"a": 1, "b": 2})

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_upsert_from_search_result_stores_reference_metadata_only(self):
        now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
        result = ExternalFoodSearchResult(
            provider="fatsecret",
            external_food_id="123",
            name="Avena",
            brand_name="",
            source_url="https://example.test/food/123",
            attribution_text="Nutrition data provided by FatSecret.",
            raw_payload={"food_id": "123", "food_name": "Avena", "calories": "389"},
        )

        recorded = upsert_external_food_reference_from_search_result(result, now=now)

        self.assertTrue(recorded.created)
        reference = recorded.reference
        self.assertEqual(reference.provider, "fatsecret")
        self.assertEqual(reference.external_food_id, "123")
        self.assertEqual(reference.external_serving_id, "")
        self.assertEqual(reference.display_name, "Avena")
        self.assertEqual(reference.seen_count, 1)
        self.assertEqual(reference.selected_count, 0)
        self.assertEqual(reference.last_fetched_at, now)
        self.assertEqual(reference.expires_at, now + timedelta(hours=24))
        self.assertEqual(len(reference.raw_payload_hash), 64)
        self.assertFalse(hasattr(reference, "raw_payload"))

    def test_upsert_from_search_result_updates_existing_reference(self):
        now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
        result = ExternalFoodSearchResult(
            provider="fatsecret",
            external_food_id="123",
            name="Avena",
            raw_payload={"food_id": "123"},
        )

        first = upsert_external_food_reference_from_search_result(result, now=now)
        second = upsert_external_food_reference_from_search_result(result, now=now + timedelta(hours=1))

        self.assertFalse(second.created)
        self.assertEqual(first.reference.pk, second.reference.pk)
        second.reference.refresh_from_db()
        self.assertEqual(second.reference.seen_count, 2)

    def test_upsert_from_detail_can_record_selected_serving_reference(self):
        now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
        serving = ExternalFoodServing(
            provider="fatsecret",
            external_food_id="123",
            external_serving_id="456",
            serving_description="100 g",
            grams="100",
            calories_kcal="389",
            protein_g="16.9",
            carbs_g="66.3",
            fat_g="6.9",
            raw_payload={"serving_id": "456", "protein": "16.9"},
        )
        detail = ExternalFoodDetail(
            provider="fatsecret",
            external_food_id="123",
            name="Avena",
            source_url="https://example.test/food/123",
            attribution_text="Nutrition data provided by FatSecret.",
            servings=(serving,),
            raw_payload={"food_id": "123", "servings": {"serving": [{"serving_id": "456"}]}},
        )

        recorded = upsert_external_food_reference_from_detail(detail, serving=serving, selected=True, now=now)

        reference = recorded.reference
        self.assertEqual(reference.external_food_id, "123")
        self.assertEqual(reference.external_serving_id, "456")
        self.assertEqual(reference.selected_count, 1)
        self.assertEqual(reference.seen_count, 1)
        self.assertEqual(len(reference.raw_payload_hash), 64)
        self.assertEqual(len(reference.detail_payload_hash), 64)
        self.assertFalse(hasattr(reference, "calories_kcal"))
        self.assertFalse(hasattr(reference, "protein_g"))

    def test_selected_detail_updates_existing_reference(self):
        serving = ExternalFoodServing(
            provider="fatsecret",
            external_food_id="123",
            external_serving_id="456",
        )
        detail = ExternalFoodDetail(
            provider="fatsecret",
            external_food_id="123",
            name="Avena",
            servings=(serving,),
        )

        upsert_external_food_reference_from_detail(detail, serving=serving, selected=True)
        recorded = upsert_external_food_reference_from_detail(detail, serving=serving, selected=True)

        self.assertFalse(recorded.created)
        recorded.reference.refresh_from_db()
        self.assertEqual(recorded.reference.selected_count, 2)
        self.assertEqual(recorded.reference.seen_count, 2)
        self.assertEqual(ExternalFoodReference.objects.count(), 1)

    def test_record_external_provider_fetch_logs_hash_without_payload(self):
        log = record_external_provider_fetch(
            provider="fatsecret",
            lookup_type=ExternalProviderFetchLog.LOOKUP_SEARCH,
            status=ExternalProviderFetchLog.STATUS_SUCCESS,
            query="avena",
            status_code=200,
            raw_payload={"foods": {"food": [{"food_id": "123"}]}},
        )

        self.assertEqual(log.provider, "fatsecret")
        self.assertEqual(log.lookup_type, ExternalProviderFetchLog.LOOKUP_SEARCH)
        self.assertEqual(log.status, ExternalProviderFetchLog.STATUS_SUCCESS)
        self.assertEqual(log.query, "avena")
        self.assertEqual(len(log.raw_payload_hash), 64)
        self.assertFalse(hasattr(log, "raw_payload"))
