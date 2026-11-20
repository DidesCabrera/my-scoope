from django.core.management import call_command
from django.test import TestCase

from food_catalog.models import CatalogFood, FoodVisualAsset
from notas.domain.models import Food


class ChileanBreadVisualPublicationTests(TestCase):
    def test_attaches_published_and_draft_catalog_foods_without_changing_nutrition(self):
        marraqueta = CatalogFood.objects.create(
            display_name="Marraqueta", status=CatalogFood.STATUS_PUBLISHED,
            protein_g_per_100g=6.4, carbs_g_per_100g=60, fat_g_per_100g=0.7,
        )
        operational = Food.objects.create(
            name="Marraqueta", protein=6.4, carbs=60, fat=0.7,
            is_global=True, catalog_food_id=marraqueta.pk,
            catalog_food_ref=marraqueta.catalog_ref,
        )
        baguette = CatalogFood.objects.create(
            display_name="Baguette", status=CatalogFood.STATUS_PUBLISHED,
            protein_g_per_100g=8.6, carbs_g_per_100g=43.6, fat_g_per_100g=2.8,
        )
        draft = CatalogFood.objects.create(
            display_name="Churrasca", status=CatalogFood.STATUS_PENDING_REVIEW,
            protein_g_per_100g=7, carbs_g_per_100g=52, fat_g_per_100g=7,
        )

        call_command("publish_chilean_bread_visuals_20261119")
        first_digest = FoodVisualAsset.objects.get(food=marraqueta).content_sha256
        call_command("publish_chilean_bread_visuals_20261119")

        self.assertEqual(FoodVisualAsset.objects.count(), 3)
        self.assertEqual(FoodVisualAsset.objects.get(food=marraqueta).content_sha256, first_digest)
        self.assertTrue(FoodVisualAsset.objects.get(food=baguette).is_published)
        self.assertFalse(FoodVisualAsset.objects.get(food=draft).is_published)
        self.assertEqual(Food.objects.get(pk=operational.pk).protein, 6.4)
        manifest = self.client.get("/api/v1/foods/visual-assets/manifest?layout=wide-v1").json()
        self.assertIn(str(operational.pk), manifest["food_ids"])
        self.assertIn("Marraqueta", manifest["images"])
        self.assertNotIn("Churrasca", manifest["images"])
