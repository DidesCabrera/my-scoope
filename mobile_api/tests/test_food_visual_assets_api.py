from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from PIL import Image

from food_catalog.admin import FoodVisualAssetForm
from food_catalog.models import CatalogFood, FoodVisualAsset
from food_catalog.visual_assets import prepare_food_visual
from notas.domain.models import Food


def png_upload(*, width=400, height=200):
    output = BytesIO()
    Image.new("RGBA", (width, height), (220, 50, 40, 255)).save(output, format="PNG")
    return SimpleUploadedFile("icon.png", output.getvalue(), content_type="image/png")


class FoodVisualAssetAPITests(TestCase):
    def setUp(self):
        self.catalog_food = CatalogFood.objects.create(
            display_name="Carne molida de vacuno magra cruda",
            status=CatalogFood.STATUS_PUBLISHED,
            protein_g_per_100g=20, carbs_g_per_100g=0, fat_g_per_100g=5,
        )
        self.food = Food.objects.create(
            name="Carne molida de vacuno magra cruda", protein=20, carbs=0, fat=5,
            is_global=True, catalog_food_id=self.catalog_food.id,
            catalog_food_ref=self.catalog_food.catalog_ref,
        )
        self.client = Client()

    def test_upload_is_normalized_without_stretching_and_requires_provenance(self):
        form = FoodVisualAssetForm(
            data={"food": self.catalog_food.pk, "is_published": True, "source_note": ""},
            files={"upload": png_upload()},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("source_note", form.errors)

        form = FoodVisualAssetForm(
            data={"food": self.catalog_food.pk, "is_published": True, "source_note": "Boceto aprobado por Felipe"},
            files={"upload": png_upload()},
        )
        self.assertTrue(form.is_valid(), form.errors)
        data, digest = form.prepared_image
        image = Image.open(BytesIO(data))
        self.assertEqual(image.size, (256, 256))
        self.assertEqual(image.getpixel((128, 128))[3], 255)
        self.assertEqual(image.getpixel((128, 1))[3], 0)
        self.assertEqual(len(digest), 64)

    def test_manifest_and_versioned_image_update_without_food_snapshot_change(self):
        data, digest = prepare_food_visual(png_upload())
        asset = FoodVisualAsset.objects.create(
            food=self.catalog_food, image_data=data, content_sha256=digest,
            is_published=True, source_note="Boceto aprobado por Felipe",
        )
        manifest = self.client.get("/api/v1/foods/visual-assets/manifest")
        self.assertEqual(manifest.status_code, 200)
        path = manifest.json()["images"][self.food.name]
        self.assertEqual(manifest.json()["food_ids"][str(self.food.id)], path)
        self.assertIn(digest, path)
        image = self.client.get(path)
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image["Content-Type"], "image/png")
        self.assertEqual(image["Cache-Control"], "public, max-age=300")
        self.assertEqual(image.content, data)

        replacement, new_digest = prepare_food_visual(png_upload(width=200, height=400))
        asset.image_data, asset.content_sha256 = replacement, new_digest
        asset.save(update_fields=["image_data", "content_sha256", "updated_at"])
        new_path = self.client.get("/api/v1/foods/visual-assets/manifest").json()["images"][self.food.name]
        self.assertNotEqual(path, new_path)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.food.refresh_from_db()
        self.assertEqual(self.food.protein, 20)

    def test_unpublished_or_unmaterialized_visual_is_not_public(self):
        data, digest = prepare_food_visual(png_upload())
        asset = FoodVisualAsset.objects.create(
            food=self.catalog_food, image_data=data, content_sha256=digest,
            is_published=False, source_note="Revisión pendiente",
        )
        self.assertEqual(self.client.get("/api/v1/foods/visual-assets/manifest").json()["images"], {})
        path = f"/api/v1/foods/visual-assets/{self.catalog_food.catalog_ref}/{digest}.png"
        self.assertEqual(self.client.get(path).status_code, 404)
        asset.is_published = True
        asset.save(update_fields=["is_published"])
        self.food.is_active = False
        self.food.save(update_fields=["is_active"])
        self.assertEqual(self.client.get("/api/v1/foods/visual-assets/manifest").json()["images"], {})
        self.assertEqual(self.client.get(path).status_code, 200)

    def test_bad_asset_path_is_rejected(self):
        self.assertEqual(self.client.get("/api/v1/foods/visual-assets/not-a-uuid/" + "a" * 64 + ".png").status_code, 404)

    def test_admin_upload_publishes_without_a_mobile_or_nutrition_change(self):
        admin = User.objects.create_superuser("visual-admin", "visual@example.com", "safe-password")
        self.client.force_login(admin)
        response = self.client.post("/admin/food_catalog/foodvisualasset/add/", {
            "food": self.catalog_food.pk,
            "upload": png_upload(),
            "is_published": "on",
            "source_note": "Ilustración interna aprobada para prueba",
            "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        asset = FoodVisualAsset.objects.get(food=self.catalog_food)
        self.assertTrue(asset.is_published)
        self.assertTrue(asset.image_data)
        self.assertEqual(len(asset.content_sha256), 64)
        self.assertIn(self.food.name, self.client.get("/api/v1/foods/visual-assets/manifest").json()["images"])
