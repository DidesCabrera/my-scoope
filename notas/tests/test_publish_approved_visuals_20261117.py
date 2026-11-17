from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from food_catalog.models import CatalogFood, CatalogPreparation, CatalogPreparationVersion, FoodVisualAsset, PreparationVisualAsset
from notas.application.services.food_catalog_snapshots import create_operational_food_snapshot_from_catalog
from notas.domain.models import Food, LegacyFoodVisualAsset, Preparation, PreparationVersion


class ApprovedVisualPublicationTests(TestCase):
    def setUp(self):
        Food.objects.create(name="Cacao", protein=19.6, carbs=20.9, fat=13.7, is_global=True)
        ají = CatalogFood.objects.create(
            display_name="Ají verde crudo", status=CatalogFood.STATUS_PUBLISHED,
            protein_g_per_100g=2, carbs_g_per_100g=9.46, fat_g_per_100g=0.2,
        )
        Food.objects.create(
            name="Ají verde crudo", protein=2, carbs=9.46, fat=0.2, is_global=True,
            catalog_food_id=ají.pk, catalog_food_ref=ají.catalog_ref,
        )
        call_command("seed_approved_oils_20261117")
        for oil in CatalogFood.objects.filter(display_name__in=["Aceite de maravilla", "Aceite de coco"]):
            create_operational_food_snapshot_from_catalog(oil)
        catalog = CatalogPreparation.objects.create(display_name="Completo italiano")
        version = CatalogPreparationVersion.objects.create(
            preparation=catalog, version=1, yield_g=179, default_portion_g=179,
            household_label="completo mediano", source_name="Receta revisada",
            yield_evidence="Porción medida", published_at=timezone.now(),
        )
        catalog.current_version = version
        catalog.save(update_fields=["current_version"])
        preparation = Preparation.objects.create(name="Completo italiano", catalog_ref=catalog.catalog_ref)
        operational = PreparationVersion.objects.create(
            preparation=preparation, version=1, release_version="test", yield_g=179,
            default_portion_g=179, household_label="completo mediano", protein_g=12,
            carbs_g=28, fat_g=26, content_sha256="test",
        )
        preparation.current_version = operational
        preparation.save(update_fields=["current_version"])

    def test_publishes_five_approved_visuals_without_changing_nutrition(self):
        before = Food.objects.get(name="Cacao").protein
        call_command("publish_approved_visuals_20261117")
        call_command("publish_approved_visuals_20261117")
        self.assertEqual(LegacyFoodVisualAsset.objects.filter(food__name="Cacao", is_published=True).count(), 1)
        self.assertEqual(FoodVisualAsset.objects.filter(food__display_name__in=[
            "Ají verde crudo", "Aceite de maravilla", "Aceite de coco",
        ], is_published=True).count(), 3)
        self.assertEqual(PreparationVisualAsset.objects.filter(preparation__display_name="Completo italiano", is_published=True).count(), 1)
        self.assertEqual(Food.objects.get(name="Cacao").protein, before)
        manifest = self.client.get("/api/v1/foods/visual-assets/manifest?layout=wide-v1").json()
        self.assertEqual(len(manifest["preparation_ids"]), 1)
        self.assertIn("Cacao", manifest["images"])
        self.assertIn("Aceite de coco", manifest["images"])
