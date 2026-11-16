import hashlib
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from PIL import Image

from food_catalog.admin import FoodVisualAssetForm
from food_catalog.models import CatalogFood, FoodVisualAsset
from food_catalog.visual_assets import prepare_food_visual
from notas.admin_food_visual_assets import LegacyFoodVisualAssetForm
from notas.domain.models import Food, LegacyFoodVisualAsset


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
        original, mobile, digest = form.prepared_image
        original_image = Image.open(BytesIO(original))
        mobile_image = Image.open(BytesIO(mobile))
        self.assertEqual(original_image.size, (256, 256))
        self.assertEqual(mobile_image.size, (192, 192))
        self.assertEqual(original_image.getpixel((128, 128))[3], 255)
        self.assertEqual(original_image.getpixel((128, 1))[3], 0)
        self.assertEqual(mobile_image.getpixel((96, 96))[3], 255)
        self.assertEqual(mobile_image.getpixel((96, 1))[3], 0)
        self.assertEqual(digest, hashlib.sha256(mobile).hexdigest())

    def test_manifest_and_versioned_image_update_without_food_snapshot_change(self):
        original, mobile, digest = prepare_food_visual(png_upload())
        asset = FoodVisualAsset.objects.create(
            food=self.catalog_food, image_data=original, mobile_image_data=mobile,
            content_sha256=digest,
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
        self.assertEqual(image.content, mobile)
        self.assertNotEqual(image.content, original)

        replacement, mobile_replacement, new_digest = prepare_food_visual(png_upload(width=200, height=400))
        asset.image_data, asset.mobile_image_data, asset.content_sha256 = replacement, mobile_replacement, new_digest
        asset.save(update_fields=["image_data", "mobile_image_data", "content_sha256", "updated_at"])
        new_path = self.client.get("/api/v1/foods/visual-assets/manifest").json()["images"][self.food.name]
        self.assertNotEqual(path, new_path)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.food.refresh_from_db()
        self.assertEqual(self.food.protein, 20)

    def test_wide_variant_crops_transparency_without_changing_square_asset(self):
        original, mobile, digest = prepare_food_visual(png_upload())
        FoodVisualAsset.objects.create(
            food=self.catalog_food, image_data=original, mobile_image_data=mobile,
            content_sha256=digest, is_published=True, source_note="Boceto aprobado por Felipe",
        )
        square_path = self.client.get("/api/v1/foods/visual-assets/manifest").json()["food_ids"][str(self.food.id)]
        wide_path = self.client.get("/api/v1/foods/visual-assets/manifest?layout=wide-v1").json()["food_ids"][str(self.food.id)]
        self.assertEqual(wide_path, square_path.replace(".png", "/wide-v1.png"))
        self.assertEqual(self.client.get(square_path).content, mobile)
        wide = self.client.get(wide_path)
        self.assertEqual(wide.status_code, 200)
        self.assertEqual(wide["ETag"], f'"{digest}-wide-v1"')
        self.assertEqual(wide["Cache-Control"], "public, max-age=300")
        self.assertEqual(wide["Content-Type"], "image/png")
        picture = Image.open(BytesIO(wide.content)).convert("RGBA")
        self.assertEqual(picture.size, (192, 127))
        self.assertEqual(picture.getchannel("A").getbbox()[2] - picture.getchannel("A").getbbox()[0], 192)
        self.assertEqual(self.client.get(wide_path.replace(digest, "a" * 64)).status_code, 404)

    def test_unpublished_or_unmaterialized_visual_is_not_public(self):
        original, mobile, digest = prepare_food_visual(png_upload())
        asset = FoodVisualAsset.objects.create(
            food=self.catalog_food, image_data=original, mobile_image_data=mobile,
            content_sha256=digest,
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
        self.assertTrue(asset.mobile_image_data)
        self.assertEqual(Image.open(BytesIO(asset.image_data)).size, (256, 256))
        self.assertEqual(Image.open(BytesIO(asset.mobile_image_data)).size, (192, 192))
        self.assertEqual(len(asset.content_sha256), 64)
        self.assertIn(self.food.name, self.client.get("/api/v1/foods/visual-assets/manifest").json()["images"])


class LegacyFoodVisualAssetAPITests(TestCase):
    def setUp(self):
        self.food = Food.objects.create(
            name="Whey Protein", protein=78.5, carbs=5.8, fat=3.8, is_global=True,
        )
        self.client = Client()

    def test_legacy_global_visual_uses_stable_id_without_nutrition_change(self):
        original, mobile, digest = prepare_food_visual(png_upload())
        asset = LegacyFoodVisualAsset.objects.create(
            food=self.food, image_data=original, mobile_image_data=mobile,
            content_sha256=digest, is_published=True,
            source_note="Ilustración interna aprobada por Felipe",
        )
        manifest = self.client.get("/api/v1/foods/visual-assets/manifest").json()
        path = manifest["food_ids"][str(self.food.id)]
        self.assertEqual(manifest["images"][self.food.name], path)
        self.assertRegex(path, r"^/api/v1/foods/visual-assets/[0-9a-f-]{36}/[0-9a-f]{64}\.png$")
        self.assertIn(str(asset.public_ref), path)
        self.assertEqual(self.client.get(path).content, mobile)
        self.assertEqual(self.food.protein, 78.5)

        replacement, mobile_replacement, new_digest = prepare_food_visual(png_upload(width=200, height=400))
        asset.image_data, asset.mobile_image_data, asset.content_sha256 = replacement, mobile_replacement, new_digest
        asset.save(update_fields=["image_data", "mobile_image_data", "content_sha256", "updated_at"])
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertNotEqual(
            self.client.get("/api/v1/foods/visual-assets/manifest").json()["food_ids"][str(self.food.id)], path,
        )

    def test_wide_variant_covers_operational_food_assignments(self):
        original, mobile, digest = prepare_food_visual(png_upload(width=200, height=400))
        asset = LegacyFoodVisualAsset.objects.create(
            food=self.food, image_data=original, mobile_image_data=mobile,
            content_sha256=digest, is_published=True, source_note="Ilustración interna aprobada",
        )
        path = self.client.get("/api/v1/foods/visual-assets/manifest?layout=wide-v1").json()["food_ids"][str(self.food.id)]
        self.assertIn(str(asset.public_ref), path)
        self.assertEqual(Image.open(BytesIO(self.client.get(path).content)).size, (192, 127))
        asset.is_published = False
        asset.save(update_fields=["is_published"])
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_one_editorial_override_applies_to_catalog_linked_food_too(self):
        catalog_food = CatalogFood.objects.create(
            display_name="Whey Protein", status=CatalogFood.STATUS_PUBLISHED,
            protein_g_per_100g=78.5, carbs_g_per_100g=5.8, fat_g_per_100g=3.8,
        )
        self.food.catalog_food_id = catalog_food.pk
        self.food.catalog_food_ref = catalog_food.catalog_ref
        self.food.save(update_fields=["catalog_food_id", "catalog_food_ref"])
        original, mobile, digest = prepare_food_visual(png_upload())
        FoodVisualAsset.objects.create(
            food=catalog_food, image_data=original, mobile_image_data=mobile,
            content_sha256=digest, is_published=True, source_note="Imagen central aprobada",
        )
        override_original, override_mobile, override_digest = prepare_food_visual(
            png_upload(width=200, height=400)
        )
        override = LegacyFoodVisualAsset.objects.create(
            food=self.food, image_data=override_original,
            mobile_image_data=override_mobile, content_sha256=override_digest,
            is_published=True, source_note="Imagen operacional aprobada",
        )
        path = self.client.get("/api/v1/foods/visual-assets/manifest").json()["food_ids"][str(self.food.pk)]
        self.assertIn(str(override.public_ref), path)
        self.assertEqual(self.client.get(path).content, override_mobile)
        self.assertEqual(self.food.protein, 78.5)

        override.is_published = False
        override.save(update_fields=["is_published"])
        fallback = self.client.get("/api/v1/foods/visual-assets/manifest").json()["food_ids"][str(self.food.pk)]
        self.assertIn(str(catalog_food.catalog_ref), fallback)
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_catalog_linked_override_requires_published_catalog_food(self):
        catalog_food = CatalogFood.objects.create(
            display_name="Whey Protein", protein_g_per_100g=78.5,
            carbs_g_per_100g=5.8, fat_g_per_100g=3.8,
        )
        self.food.catalog_food_id = catalog_food.pk
        self.food.catalog_food_ref = catalog_food.catalog_ref
        self.food.save(update_fields=["catalog_food_id", "catalog_food_ref"])
        form = LegacyFoodVisualAssetForm(
            data={"food": self.food.pk, "is_published": True, "source_note": "Aprobada"},
            files={"upload": png_upload()},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("is_published", form.errors)

        original, mobile, digest = prepare_food_visual(png_upload())
        override = LegacyFoodVisualAsset.objects.create(
            food=self.food, image_data=original, mobile_image_data=mobile,
            content_sha256=digest, is_published=True, source_note="Imagen aprobada",
        )
        self.assertNotIn(str(self.food.pk), self.client.get("/api/v1/foods/visual-assets/manifest").json()["food_ids"])
        path = f"/api/v1/foods/visual-assets/{override.public_ref}/{digest}.png"
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_private_inactive_linked_and_unpublished_foods_are_not_exposed(self):
        original, mobile, digest = prepare_food_visual(png_upload())
        asset = LegacyFoodVisualAsset.objects.create(
            food=self.food, image_data=original, mobile_image_data=mobile,
            content_sha256=digest, is_published=False, source_note="Revisión pendiente",
        )
        path = f"/api/v1/foods/visual-assets/legacy/{self.food.id}/{digest}.png"
        self.assertNotIn(str(self.food.id), self.client.get("/api/v1/foods/visual-assets/manifest").json()["food_ids"])
        self.assertEqual(self.client.get(path).status_code, 404)
        asset.is_published = True
        asset.save(update_fields=["is_published"])
        self.food.is_global = False
        self.food.save(update_fields=["is_global"])
        self.assertEqual(self.client.get(path).status_code, 404)
        self.food.is_global = True
        self.food.is_active = False
        self.food.save(update_fields=["is_global", "is_active"])
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_admin_rejects_non_global_food_and_requires_provenance(self):
        form = LegacyFoodVisualAssetForm(
            data={"food": self.food.pk, "is_published": True, "source_note": ""},
            files={"upload": png_upload()},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("source_note", form.errors)
        self.food.is_global = False
        self.food.save(update_fields=["is_global"])
        form = LegacyFoodVisualAssetForm(
            data={"food": self.food.pk, "is_published": True, "source_note": "Aprobado"},
            files={"upload": png_upload()},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("food", form.errors)
