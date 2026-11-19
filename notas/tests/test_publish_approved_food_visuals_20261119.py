from django.core.management import call_command
from django.test import TestCase

from food_catalog.models import CatalogFood
from notas.domain.models import Food, LegacyFoodVisualAsset


class ApprovedFoodVisualPublicationTests(TestCase):
    def test_publishes_all_five_and_replaces_existing_image_without_nutrition_changes(self):
        from notas.management.commands.publish_approved_food_visuals_20261119 import APPROVED

        for name, _ in APPROVED:
            catalog = CatalogFood.objects.create(
                display_name=name, status=CatalogFood.STATUS_PUBLISHED,
                protein_g_per_100g=7, carbs_g_per_100g=8, fat_g_per_100g=9,
            )
            food = Food.objects.create(
                name=name, protein=7, carbs=8, fat=9, is_global=True,
                catalog_food_ref=catalog.catalog_ref, catalog_food_id=catalog.pk,
            )
            if name == "Coliflor cocida":
                LegacyFoodVisualAsset.objects.create(
                    food=food, image_data=b"old", mobile_image_data=b"old",
                    content_sha256="old", is_published=True,
                )

        call_command("publish_approved_food_visuals_20261119")
        call_command("publish_approved_food_visuals_20261119")

        self.assertEqual(LegacyFoodVisualAsset.objects.filter(is_published=True).count(), 5)
        for name, _ in APPROVED:
            food = Food.objects.get(name=name)
            self.assertEqual((food.protein, food.carbs, food.fat), (7, 8, 9))
            self.assertEqual(len(food.legacy_visual_asset.content_sha256), 64)
        self.assertIn(
            "Coliflor cocida",
            self.client.get("/api/v1/foods/visual-assets/manifest?layout=wide-v1").json()["images"],
        )
