from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from admin_analytics.selectors.food_catalog import get_food_catalog_metrics
from food_catalog.models import (
    CatalogCurationCandidate,
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
    CatalogImportBatch,
    ExternalFoodReference,
    ExternalProviderFetchLog,
)


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminAnalyticsFoodCatalogMetricsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="password123",
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username="member@example.com",
            email="member@example.com",
            password="password123",
        )

    def _create_catalog_data(self):
        published_food = CatalogFood.objects.create(
            display_name="Avena",
            canonical_name="avena",
            country="CL",
            protein_g_per_100g=Decimal("13.000"),
            carbs_g_per_100g=Decimal("60.000"),
            fat_g_per_100g=Decimal("7.000"),
            calories_kcal_per_100g=Decimal("355.000"),
            status=CatalogFood.STATUS_PUBLISHED,
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            data_quality_score=90,
            confidence_score=Decimal("95.00"),
            solver_enabled=True,
            created_by=self.member,
        )
        review_food = CatalogFood.objects.create(
            display_name="Yogur marca",
            canonical_name="yogur marca",
            brand_name="Marca",
            country="CL",
            is_branded=True,
            protein_g_per_100g=Decimal("8.000"),
            carbs_g_per_100g=Decimal("5.000"),
            fat_g_per_100g=Decimal("2.000"),
            status=CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
            source_type=CatalogFood.SOURCE_BRAND_SUBMITTED,
            data_quality_score=45,
            created_by=self.member,
        )
        CatalogFoodPortion.objects.create(catalog_food=published_food, label="100 g", grams=Decimal("100.000"))
        CatalogFoodAlias.objects.create(
            catalog_food=published_food,
            name="oats",
            normalized_name="oats",
            alias_type=CatalogFoodAlias.ALIAS_SEARCH,
        )
        CatalogFoodSource.objects.create(
            catalog_food=published_food,
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="Internal seed",
            source_food_id="seed-1",
            license_status=CatalogFoodSource.LICENSE_ALLOWED,
        )
        CatalogImportBatch.objects.create(
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="Seed import",
            status=CatalogImportBatch.STATUS_COMPLETED,
            total_rows=10,
            imported_rows=8,
            skipped_rows=1,
            failed_rows=1,
        )
        reference = ExternalFoodReference.objects.create(
            provider=CatalogFood.SOURCE_OPEN_FOOD_FACTS,
            external_food_id="off-1",
            display_name="External oats",
            seen_count=4,
            selected_count=2,
        )
        ExternalProviderFetchLog.objects.create(
            provider=CatalogFood.SOURCE_OPEN_FOOD_FACTS,
            lookup_type=ExternalProviderFetchLog.LOOKUP_SEARCH,
            status=ExternalProviderFetchLog.STATUS_SUCCESS,
            query="avena",
        )
        ExternalProviderFetchLog.objects.create(
            provider=CatalogFood.SOURCE_OPEN_FOOD_FACTS,
            lookup_type=ExternalProviderFetchLog.LOOKUP_DETAIL,
            status=ExternalProviderFetchLog.STATUS_FAILED,
            external_food_id="off-1",
            error_message="provider error",
        )
        CatalogCurationCandidate.objects.create(
            external_reference=reference,
            provider=CatalogFood.SOURCE_OPEN_FOOD_FACTS,
            external_food_id="off-1",
            display_name="External oats",
            status=CatalogCurationCandidate.STATUS_QUEUED,
            reason=CatalogCurationCandidate.REASON_EXTERNAL_SELECTED,
            priority=80,
            created_by=self.member,
        )
        return published_food, review_food

    def test_selector_returns_food_catalog_quality_curation_and_provider_metrics(self):
        self._create_catalog_data()

        metrics = get_food_catalog_metrics()

        self.assertEqual(metrics["catalog"]["foods_total"], 2)
        self.assertEqual(metrics["catalog"]["published"], 1)
        self.assertEqual(metrics["catalog"]["solver_enabled"], 1)
        self.assertEqual(metrics["catalog"]["low_quality"], 1)
        self.assertEqual(metrics["catalog"]["needs_more_evidence"], 1)
        self.assertEqual(metrics["evidence"]["portions_total"], 1)
        self.assertEqual(metrics["evidence"]["aliases_total"], 1)
        self.assertEqual(metrics["evidence"]["sources_total"], 1)
        self.assertEqual(metrics["evidence"]["foods_without_sources"], 1)
        self.assertEqual(metrics["imports"]["batches_total"], 1)
        self.assertEqual(metrics["imports"]["imported_rows"], 8)
        self.assertEqual(metrics["external"]["references_total"], 1)
        self.assertEqual(metrics["external"]["fetch_logs_7d"], 2)
        self.assertEqual(metrics["external"]["fetch_failed_7d"], 1)
        self.assertEqual(metrics["curation"]["candidates_total"], 1)
        self.assertEqual(metrics["curation"]["queued"], 1)
        self.assertEqual(metrics["catalog"]["status_rows"][0]["total"], 1)

    def test_food_catalog_dashboard_is_staff_only_and_renders_metrics(self):
        self._create_catalog_data()

        response = self.client.get(reverse("admin_analytics_food_catalog"))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin_analytics_food_catalog"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Food Catalog Analytics")
        self.assertContains(response, "Inventario maestro")
        self.assertContains(response, "Calidad y completitud")
        self.assertContains(response, "Estados de curaduría")
        self.assertContains(response, "External providers")
        self.assertContains(response, "Curation queue")
        self.assertContains(response, "open_food_facts")
