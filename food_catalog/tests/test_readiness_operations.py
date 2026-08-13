import json
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from food_catalog.infrastructure.readiness_audit import audit_catalog_readiness
from food_catalog.infrastructure.source_portion_backfill import backfill_source_portions
from food_catalog.models import CatalogFood, CatalogFoodPortion, CatalogFoodSource


class CatalogReadinessAuditTests(TestCase):
    def setUp(self):
        self.food = _food(source_food_id="175180")

    def test_audit_distinguishes_source_and_internal_completeness(self):
        audit = audit_catalog_readiness()
        self.assertEqual((audit.source_complete, audit.internally_incomplete), (1, 1))
        self.assertFalse(audit.passes)
        self.assertEqual(audit.missing_counts["default_portion_g"], 1)

        _make_ready(self.food)
        audit = audit_catalog_readiness()
        self.assertTrue(audit.passes)
        self.assertEqual(audit.invalid_solver_food_ids, ())

    def test_audit_command_has_stable_json_contract(self):
        output = StringIO()
        call_command("audit_catalog_readiness", include_foods=True, stdout=output)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["source_complete"], 1)
        self.assertEqual(payload["foods"][0]["source"]["food_id"], "175180")
        self.assertIn("passes", payload)


class CatalogSourcePortionBackfillTests(TestCase):
    def setUp(self):
        self.food = _food(source_food_id="175180", evidence_payload={})

    def test_dry_run_does_not_mutate_source(self):
        result = backfill_source_portions(limit=10)
        self.assertEqual((result.proposed, result.applied), (1, 0))
        self.assertEqual(self.food.sources.get().evidence_payload, {})

    def test_apply_records_evidence_and_trace(self):
        result = backfill_source_portions(limit=10, apply=True, reason="Historical evidence repair.")
        source = self.food.sources.get()
        self.assertEqual((result.applied, result.remaining), (1, 0))
        self.assertEqual(source.evidence_payload["source_portions"][0]["grams"], "85.000")
        self.assertEqual(
            source.evidence_payload["source_portions_provenance"]["batch_ref"],
            result.batch_ref,
        )
        self.assertIsNotNone(source.last_checked_at)


def _food(*, source_food_id, evidence_payload=None):
    food = CatalogFood.objects.create(
        display_name="Camarón cocido",
        canonical_name=f"camaron-{source_food_id}",
        food_group="finfish_and_shellfish_products",
        food_subgroup="shellfish",
        preparation_state=CatalogFood.PREPARATION_COOKED,
        protein_g_per_100g=Decimal("24"),
        carbs_g_per_100g=Decimal("0.2"),
        fat_g_per_100g=Decimal("0.28"),
        data_quality_score=90,
        status=CatalogFood.STATUS_PENDING_REVIEW,
    )
    CatalogFoodSource.objects.create(
        catalog_food=food,
        source_type=CatalogFood.SOURCE_USDA,
        source_name="USDA FoodData Central",
        source_food_id=source_food_id,
        source_dataset="sr_legacy",
        source_version="2018-04",
        source_url=f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{source_food_id}/nutrients",
        license_status=CatalogFoodSource.LICENSE_ALLOWED,
        evidence_payload=evidence_payload if evidence_payload is not None else {
            "source_portions": [{"amount": "3", "grams": "85", "modifier": "oz"}],
        },
    )
    return food


def _make_ready(food):
    CatalogFoodPortion.objects.create(
        catalog_food=food, label="3 oz", grams=Decimal("85"), is_default=True,
    )
    food.solver_min_portion_g = Decimal("50")
    food.solver_max_portion_g = Decimal("300")
    food.solver_portion_step_g = Decimal("10")
    food.solver_enabled = True
    food.food_form = CatalogFood.FOOD_FORM_INGREDIENT
    food.functional_roles = ["lean_protein"]
    food.meal_affinities = ["lunch", "dinner"]
    food.preparation_effort = CatalogFood.PREPARATION_EFFORT_NONE
    food.cost_band = CatalogFood.COST_BAND_HIGH
    food.save()
