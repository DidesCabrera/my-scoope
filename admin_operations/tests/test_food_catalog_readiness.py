from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from admin_operations.models import AdminOperationAuditEvent
from food_catalog.models import CatalogEnrichmentBatch, CatalogFood, CatalogFoodSource


class AdminOperationsFoodCatalogReadinessTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(username="readiness-ops", is_staff=True)
        self.food = _create_food()
        self.client.force_login(self.staff)

    def test_readiness_page_shows_audit_queue_and_navigation_tab(self):
        response = self.client.get(reverse("admin_operations_food_catalog_readiness"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Readiness del Food Catalog")
        self.assertContains(response, "Alimentos con campos internos pendientes")
        self.assertContains(response, self.food.display_name)
        self.assertContains(response, "USDA FoodData Central · 175180")
        self.assertContains(response, "Preparar propuestas")

    def test_prepare_review_and_apply_work_inside_admin_operations(self):
        response = self.client.post(
            reverse("admin_operations_food_catalog_readiness_prepare"),
            {
                "food_ids": [str(self.food.pk)],
                "environment": "staging",
                "reason": "Preparar revisión desde Admin Operations.",
            },
        )
        batch = CatalogEnrichmentBatch.objects.get()
        self.assertRedirects(
            response,
            reverse("admin_operations_food_catalog_readiness_batch", args=[batch.batch_ref]),
        )
        self.food.refresh_from_db()
        self.assertFalse(self.food.solver_enabled)
        self.assertFalse(self.food.portions.exists())

        detail = self.client.get(reverse(
            "admin_operations_food_catalog_readiness_batch", args=[batch.batch_ref]
        ))
        self.assertContains(detail, "Revisión agrupada por alimento")
        self.assertContains(detail, self.food.display_name)
        self.assertContains(detail, "default_portion_g")
        self.assertContains(detail, "85")
        self.assertContains(detail, "catalog-readiness.cl.v1")
        self.assertContains(detail, "Aplicar propuestas")

        apply_response = self.client.post(
            reverse("admin_operations_food_catalog_readiness_batch_action", args=[batch.batch_ref]),
            {"action": "apply", "reason": "Aplicar lote revisado."},
        )
        self.assertRedirects(
            apply_response,
            reverse("admin_operations_food_catalog_readiness_batch", args=[batch.batch_ref]),
        )
        self.food.refresh_from_db()
        self.assertTrue(self.food.solver_enabled)
        self.assertEqual(self.food.status, CatalogFood.STATUS_PENDING_REVIEW)
        self.assertIsNone(self.food.published_at)
        self.assertEqual(
            AdminOperationAuditEvent.objects.filter(action__startswith="food_catalog.readiness.").count(),
            2,
        )

    def test_source_portion_backfill_is_available_and_traced(self):
        source = self.food.sources.get()
        source.evidence_payload = {}
        source.save(update_fields=["evidence_payload"])

        self.client.post(
            reverse("admin_operations_food_catalog_source_portions_backfill"),
            {"mode": "dry_run", "limit": "10", "after_id": "0", "reason": "Comprobar."},
        )
        source.refresh_from_db()
        self.assertEqual(source.evidence_payload, {})

        self.client.post(
            reverse("admin_operations_food_catalog_source_portions_backfill"),
            {"mode": "apply", "limit": "10", "after_id": "0", "reason": "Reparar evidencia histórica."},
        )
        source.refresh_from_db()
        self.assertEqual(source.evidence_payload["source_portions"][0]["grams"], "85.000")
        self.assertEqual(
            AdminOperationAuditEvent.objects.filter(action__startswith="food_catalog.source_portions.").count(),
            2,
        )


def _create_food():
    food = CatalogFood.objects.create(
        display_name="Camarón cocido",
        canonical_name="camaron-cocido-readiness-ops",
        food_group="finfish_and_shellfish_products",
        food_subgroup="shellfish",
        preparation_state=CatalogFood.PREPARATION_COOKED,
        protein_g_per_100g=Decimal("24"),
        carbs_g_per_100g=Decimal("0.2"),
        fat_g_per_100g=Decimal("0.28"),
        data_quality_score=90,
        status=CatalogFood.STATUS_PENDING_REVIEW,
        source_type=CatalogFood.SOURCE_USDA,
    )
    CatalogFoodSource.objects.create(
        catalog_food=food,
        source_type=CatalogFood.SOURCE_USDA,
        source_name="USDA FoodData Central",
        source_food_id="175180",
        source_dataset="sr_legacy",
        source_version="2018-04",
        source_url="https://fdc.nal.usda.gov/fdc-app.html#/food-details/175180/nutrients",
        license_status=CatalogFoodSource.LICENSE_ALLOWED,
        evidence_payload={
            "source_portions": [{"amount": "3", "grams": "85", "modifier": "oz"}],
        },
    )
    return food
