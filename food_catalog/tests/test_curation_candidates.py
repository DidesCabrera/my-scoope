from django.core.management import call_command
from django.test import TestCase

from food_catalog.application.curation_candidates import (
    queue_external_reference_for_curation,
    queue_external_references_for_curation,
    should_queue_external_reference,
)
from food_catalog.models import CatalogCurationCandidate, ExternalFoodReference


class CurationCandidateQueueTests(TestCase):
    def create_reference(self, **overrides):
        defaults = {
            "provider": "fatsecret",
            "external_food_id": "fs-1",
            "external_serving_id": "",
            "display_name": "Avena FatSecret",
            "brand_name": "",
            "source_url": "https://example.test/foods/fs-1",
            "attribution_text": "Nutrition data provided by FatSecret.",
            "seen_count": 3,
            "selected_count": 0,
            "is_active": True,
        }
        defaults.update(overrides)
        return ExternalFoodReference.objects.create(**defaults)

    def test_should_queue_reference_when_selected_or_frequently_seen(self):
        selected = self.create_reference(external_food_id="selected", seen_count=1, selected_count=1)
        frequently_seen = self.create_reference(external_food_id="seen", seen_count=3, selected_count=0)
        ignored = self.create_reference(external_food_id="ignored", seen_count=2, selected_count=0)
        inactive = self.create_reference(external_food_id="inactive", seen_count=10, selected_count=10, is_active=False)

        self.assertTrue(should_queue_external_reference(selected))
        self.assertTrue(should_queue_external_reference(frequently_seen))
        self.assertFalse(should_queue_external_reference(ignored))
        self.assertFalse(should_queue_external_reference(inactive))

    def test_queue_reference_creates_candidate_without_catalog_or_operational_food(self):
        reference = self.create_reference(selected_count=1)

        result = queue_external_reference_for_curation(reference)

        self.assertTrue(result.created)
        candidate = result.candidate
        self.assertEqual(candidate.external_reference, reference)
        self.assertEqual(candidate.provider, "fatsecret")
        self.assertEqual(candidate.external_food_id, "fs-1")
        self.assertEqual(candidate.display_name, "Avena FatSecret")
        self.assertEqual(candidate.status, CatalogCurationCandidate.STATUS_QUEUED)
        self.assertEqual(candidate.reason, CatalogCurationCandidate.REASON_EXTERNAL_SELECTED)
        self.assertGreaterEqual(candidate.priority, 80)
        self.assertEqual(candidate.seen_count_at_creation, 3)
        self.assertEqual(candidate.selected_count_at_creation, 1)
        self.assertFalse(hasattr(candidate, "protein_g_per_100g"))
        self.assertFalse(hasattr(candidate, "calories_kcal_per_100g"))

    def test_queue_reference_updates_existing_candidate(self):
        reference = self.create_reference(seen_count=3, selected_count=0)
        first = queue_external_reference_for_curation(reference)
        reference.display_name = "Avena actualizada"
        reference.selected_count = 2
        reference.save(update_fields=["display_name", "selected_count"])

        second = queue_external_reference_for_curation(reference)

        self.assertFalse(second.created)
        self.assertEqual(first.candidate.pk, second.candidate.pk)
        second.candidate.refresh_from_db()
        self.assertEqual(second.candidate.display_name, "Avena actualizada")
        self.assertEqual(second.candidate.reason, CatalogCurationCandidate.REASON_EXTERNAL_SELECTED)
        self.assertEqual(second.candidate.selected_count_at_creation, 2)
        self.assertEqual(CatalogCurationCandidate.objects.count(), 1)

    def test_bulk_queue_skips_low_demand_references(self):
        self.create_reference(external_food_id="eligible-selected", seen_count=1, selected_count=1)
        self.create_reference(external_food_id="eligible-seen", seen_count=3, selected_count=0)
        self.create_reference(external_food_id="low-demand", seen_count=1, selected_count=0)

        result = queue_external_references_for_curation()

        self.assertEqual(result.created_count, 2)
        self.assertEqual(result.updated_count, 0)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(CatalogCurationCandidate.objects.count(), 2)

    def test_management_command_dry_run_does_not_create_candidates(self):
        self.create_reference(selected_count=1)

        call_command("queue_catalog_external_curation_candidates", "--dry-run")

        self.assertEqual(CatalogCurationCandidate.objects.count(), 0)

    def test_management_command_queues_candidates(self):
        self.create_reference(selected_count=1)

        call_command("queue_catalog_external_curation_candidates")

        self.assertEqual(CatalogCurationCandidate.objects.count(), 1)
