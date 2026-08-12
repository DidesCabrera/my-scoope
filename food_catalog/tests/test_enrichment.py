from decimal import Decimal

from django.test import TestCase

from food_catalog.infrastructure.enrichment import (
    CatalogEnrichmentError,
    apply_enrichment_batch,
    audit_catalog_enrichment,
    create_enrichment_batch,
    dry_run_enrichment_manifest,
    revert_enrichment_batch,
)
from food_catalog.models import (
    CatalogCapabilityDefinition,
    CatalogClientRequirement,
    CatalogEnrichmentChange,
    CatalogFood,
    CatalogFoodCapability,
    CatalogFoodPortion,
)


class CatalogEnrichmentTests(TestCase):
    def setUp(self):
        self.food = CatalogFood.objects.create(
            display_name="Lentejas cocidas",
            canonical_name="lentejas cocidas",
            food_group="legumes",
            preparation_state=CatalogFood.PREPARATION_COOKED,
            protein_g_per_100g=Decimal("9"),
            carbs_g_per_100g=Decimal("20"),
            fat_g_per_100g=Decimal("0.4"),
        )
        CatalogFoodPortion.objects.create(
            catalog_food=self.food, label="1 taza", grams=Decimal("180"), is_default=True
        )
        self.batch = create_enrichment_batch(
            foods=[self.food], environment="production", reason="Complete solver data."
        )

    def _manifest(self, *, field_name="solver_min_portion_g", value="60.000"):
        return {
            "batch_ref": str(self.batch.batch_ref),
            "contract_version": "catalog-enrichment.v1",
            "food_proposals": [{
                "catalog_food_id": self.food.pk,
                "expected_updated_at": self.food.updated_at.isoformat(),
                "profile_key": "cooked_legume",
                "changes": [{
                    "field_name": field_name,
                    "proposed_value": value,
                    "nature": "operational",
                    "provenance": ["internal_policy", "ai_assisted"],
                    "consumers": ["nutrition_solver"],
                    "maturity": "stable",
                    "authority_requirement": "internal_review",
                    "risk_level": "medium",
                    "assessment_status": "proposed",
                    "confidence": 92,
                    "rationale": "Cooked-legume profile adjusted to the approved 180 g default portion.",
                }],
            }],
        }

    def test_valid_dry_run_does_not_modify_catalog_food(self):
        result = dry_run_enrichment_manifest(batch=self.batch, manifest=self._manifest())
        self.food.refresh_from_db()

        self.assertEqual(result.valid, 1)
        self.assertEqual(result.invalid, 0)
        self.assertIsNone(self.food.solver_min_portion_g)
        self.assertEqual(self.batch.proposals.get().nature, "operational")
        self.assertEqual(self.batch.proposals.get().consumers, ["nutrition_solver"])

    def test_apply_records_change_and_does_not_publish(self):
        manifest = self._manifest()
        dry_run_enrichment_manifest(batch=self.batch, manifest=manifest)
        apply_enrichment_batch(batch=self.batch, manifest=manifest, reason="Approved bounded production batch.")
        self.food.refresh_from_db()

        self.assertEqual(self.food.solver_min_portion_g, Decimal("60"))
        self.assertEqual(self.food.status, CatalogFood.STATUS_MANUAL_CANDIDATE)
        change = CatalogEnrichmentChange.objects.get(action=CatalogEnrichmentChange.ACTION_APPLY)
        self.assertIsNone(change.value_before)
        self.assertEqual(change.value_after, "60.000")

    def test_default_portion_proposal_is_reversible_and_does_not_publish(self):
        self.food.portions.all().delete()
        self.food.save(update_fields=["updated_at"])
        self.batch = create_enrichment_batch(
            foods=[self.food], environment="production", reason="Propose default portion."
        )
        manifest = self._manifest(field_name="default_portion_g", value="180.000")

        result = dry_run_enrichment_manifest(batch=self.batch, manifest=manifest)
        self.assertEqual((result.valid, result.invalid), (1, 0))
        self.assertFalse(self.food.portions.exists())

        apply_enrichment_batch(batch=self.batch, manifest=manifest, reason="Apply proposed portion.")
        portion = self.food.portions.get(is_default=True)
        self.assertEqual(portion.grams, Decimal("180"))
        self.assertEqual(portion.source, "internal_policy_ai_assisted")
        self.food.refresh_from_db()
        self.assertEqual(self.food.status, CatalogFood.STATUS_MANUAL_CANDIDATE)

        revert_enrichment_batch(batch=self.batch, reason="Revert proposed portion.")
        self.assertFalse(self.food.portions.filter(is_default=True).exists())

    def test_revert_creates_compensating_ledger_event(self):
        manifest = self._manifest()
        dry_run_enrichment_manifest(batch=self.batch, manifest=manifest)
        apply_enrichment_batch(batch=self.batch, manifest=manifest, reason="Apply.")
        revert_enrichment_batch(batch=self.batch, reason="Validated rollback.")
        self.food.refresh_from_db()

        self.assertIsNone(self.food.solver_min_portion_g)
        self.assertEqual(
            list(self.batch.changes.values_list("action", flat=True)),
            [CatalogEnrichmentChange.ACTION_APPLY, CatalogEnrichmentChange.ACTION_REVERT],
        )

    def test_nutrition_and_status_are_not_enrichable(self):
        for forbidden in ("protein_g_per_100g", "status"):
            batch = self.batch if forbidden == "protein_g_per_100g" else create_enrichment_batch(
                foods=[self.food], environment="production", reason="Forbidden field test."
            )
            self.batch = batch
            manifest = self._manifest(field_name=forbidden, value="99")
            result = dry_run_enrichment_manifest(batch=batch, manifest=manifest)
            self.assertEqual(result.invalid, 1)
            self.assertIn("not enrichable", batch.proposals.get().validation_errors[0])

    def test_apply_rejects_manifest_changed_after_dry_run(self):
        manifest = self._manifest()
        dry_run_enrichment_manifest(batch=self.batch, manifest=manifest)
        changed = {**manifest, "extra": True}
        with self.assertRaisesMessage(CatalogEnrichmentError, "does not match"):
            apply_enrichment_batch(batch=self.batch, manifest=changed, reason="Apply.")

    def test_capability_dimensions_and_client_requirement_are_independent(self):
        definition = CatalogCapabilityDefinition.objects.create(
            key="texture",
            schema_version="v1",
            label="Texture",
            data_type="enum_list",
            nature=CatalogCapabilityDefinition.NATURE_SEMANTIC,
            maturity=CatalogCapabilityDefinition.MATURITY_EXPERIMENTAL,
            consumers=["nutrition_solver", "meal_grammar"],
            authority_requirement=CatalogCapabilityDefinition.AUTHORITY_INTERNAL,
            risk_level=CatalogCapabilityDefinition.RISK_LOW,
        )
        CatalogClientRequirement.objects.create(
            client_key="nutrition_solver", requirement_version="v3", capability=definition, is_required=True
        )
        audit = audit_catalog_enrichment()
        self.assertEqual(audit.client_requirement_gaps["texture@v1"], 1)

        CatalogFoodCapability.objects.create(
            catalog_food=self.food,
            definition=definition,
            value=["soft"],
            assessment_status=CatalogFoodCapability.STATUS_CONFIRMED_VALUE,
            provenance=["internal_policy", "ai_assisted"],
            generation_method="codex_assisted",
        )
        self.assertEqual(audit_catalog_enrichment().client_requirement_gaps["texture@v1"], 0)

    def test_capability_apply_and_revert_restore_absence(self):
        definition = CatalogCapabilityDefinition.objects.create(
            key="texture", schema_version="v1", label="Texture", data_type="enum_list",
            nature=CatalogCapabilityDefinition.NATURE_SEMANTIC,
            maturity=CatalogCapabilityDefinition.MATURITY_EXPERIMENTAL,
            consumers=["nutrition_solver"],
            authority_requirement=CatalogCapabilityDefinition.AUTHORITY_INTERNAL,
            risk_level=CatalogCapabilityDefinition.RISK_LOW,
        )
        manifest = {
            "batch_ref": str(self.batch.batch_ref),
            "contract_version": "catalog-enrichment.v1",
            "food_proposals": [{
                "catalog_food_id": self.food.pk,
                "expected_updated_at": self.food.updated_at.isoformat(),
                "changes": [{
                    "capability_key": definition.key,
                    "capability_version": definition.schema_version,
                    "proposed_value": ["soft"],
                    "nature": "semantic",
                    "provenance": ["internal_policy", "ai_assisted"],
                    "consumers": ["nutrition_solver"],
                    "maturity": "experimental",
                    "authority_requirement": "internal_review",
                    "risk_level": "low",
                    "assessment_status": "proposed",
                    "confidence": 85,
                    "rationale": "Experimental solver capability.",
                }],
            }],
        }
        dry_run_enrichment_manifest(batch=self.batch, manifest=manifest)
        apply_enrichment_batch(batch=self.batch, manifest=manifest, reason="Apply experimental capability.")
        self.assertEqual(CatalogFoodCapability.objects.get().value, ["soft"])

        revert_enrichment_batch(batch=self.batch, reason="Revert experimental capability.")
        self.assertFalse(CatalogFoodCapability.objects.exists())
