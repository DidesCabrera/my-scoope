from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from food_catalog.infrastructure.readiness_pipeline import prepare_readiness_batch
from food_catalog.models import CatalogEnrichmentBatch, CatalogFood, CatalogFoodSource


class CatalogReadinessPipelineTests(TestCase):
    def setUp(self):
        self.food = CatalogFood.objects.create(
            display_name="Camarón cocido", canonical_name="camaron cocido",
            food_group="finfish_and_shellfish_products", food_subgroup="shellfish",
            preparation_state=CatalogFood.PREPARATION_COOKED,
            protein_g_per_100g=Decimal("24"), carbs_g_per_100g=Decimal("0.2"),
            fat_g_per_100g=Decimal("0.28"), data_quality_score=90,
            status=CatalogFood.STATUS_PENDING_REVIEW,
        )
        CatalogFoodSource.objects.create(
            catalog_food=self.food, source_type=CatalogFood.SOURCE_USDA,
            source_name="USDA FoodData Central", source_food_id="175180",
            source_dataset="sr_legacy", source_version="2018-04",
            source_url="https://fdc.nal.usda.gov/fdc-app.html#/food-details/175180/nutrients",
            license_status=CatalogFoodSource.LICENSE_ALLOWED,
        )

    def test_prepare_generates_all_mandatory_missing_fields_without_mutation(self):
        batch, result, skipped = prepare_readiness_batch(
            foods=CatalogFood.objects.filter(pk=self.food.pk),
            environment="production", reason="Complete readiness.",
        )
        self.food.refresh_from_db()

        self.assertEqual((result.valid, result.invalid), (10, 0))
        self.assertEqual(skipped, [])
        self.assertEqual(batch.status, CatalogEnrichmentBatch.STATUS_DRY_RUN_VALID)
        self.assertEqual(batch.manifest_payload["food_proposals"][0]["changes"][0]["field_name"], "default_portion_g")
        self.assertFalse(self.food.portions.exists())
        self.assertFalse(self.food.solver_enabled)

    def test_stored_manifest_apply_completes_food_and_keeps_pending_review(self):
        batch, _result, _skipped = prepare_readiness_batch(
            foods=CatalogFood.objects.filter(pk=self.food.pk),
            environment="production", reason="Complete readiness.",
        )
        call_command(
            "apply_catalog_readiness_batch", str(batch.batch_ref),
            reason="Apply exact stored manifest.", confirm_apply=True,
        )
        self.food.refresh_from_db()

        self.assertEqual(self.food.portions.get(is_default=True).grams, Decimal("85"))
        self.assertEqual(self.food.food_form, CatalogFood.FOOD_FORM_INGREDIENT)
        self.assertEqual(self.food.functional_roles, ["lean_protein"])
        self.assertTrue(self.food.solver_enabled)
        self.assertEqual(self.food.status, CatalogFood.STATUS_PENDING_REVIEW)
        self.assertIsNone(self.food.published_at)
        self.assertEqual(batch.changes.filter(action="apply").count(), 10)

    def test_source_portion_candidates_support_future_imports(self):
        source = self.food.sources.get()
        source.source_food_id = "future"
        source.evidence_payload = {
            "source_portions": [{"amount": "1", "grams": "150", "modifier": "NLEA serving"}]
        }
        source.save()
        batch, result, skipped = prepare_readiness_batch(
            foods=CatalogFood.objects.filter(pk=self.food.pk),
            environment="staging", reason="Future import readiness.",
        )
        proposal = batch.proposals.get(field_name="default_portion_g")
        self.assertEqual((result.invalid, skipped, proposal.proposed_value), (0, [], "150"))

    def test_prepare_command_selects_incomplete_food_and_preserves_existing_values(self):
        self.food.cost_band = CatalogFood.COST_BAND_MEDIUM
        self.food.save(update_fields=["cost_band", "updated_at"])
        output = StringIO()

        call_command(
            "prepare_catalog_readiness",
            environment="production",
            reason="Prepare compact readiness wave.",
            ids=str(self.food.pk),
            stdout=output,
        )

        batch = CatalogEnrichmentBatch.objects.latest("id")
        self.assertEqual(batch.status, CatalogEnrichmentBatch.STATUS_DRY_RUN_VALID)
        self.assertEqual(batch.total_proposals, 9)
        self.assertFalse(batch.proposals.filter(field_name="cost_band").exists())
        self.assertIn('"valid_proposals": 9', output.getvalue())
