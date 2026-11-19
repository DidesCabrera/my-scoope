"""Publish the five food illustrations approved on 2026-11-19."""

from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from food_catalog.models import CatalogFood
from food_catalog.visual_assets import prepare_food_visual
from notas.domain.models import Food, LegacyFoodVisualAsset

ASSETS = Path(__file__).resolve().parents[3] / "docs/10_active_cycles/assets/visual_identity_catalog"
APPROVED = (
    ("Coliflor cocida", "cauliflower-cooked-bowl-approved.png"),
    ("Palmito crudo", "heart-of-palm-raw-approved.png"),
    ("Okra cruda", "okra-raw-approved.png"),
    ("Melón calameño crudo", "calameno-melon-raw-approved.png"),
    ("Langosta cocida", "lobster-cooked-approved.png"),
)


class Command(BaseCommand):
    help = "Publish five approved food illustrations without changing nutritional data."

    def handle(self, *args, **options):
        prepared = []
        for name, filename in APPROVED:
            path = ASSETS / filename
            if not path.is_file():
                raise CommandError(f"Approved image missing: {path}")
            image = prepare_food_visual(
                SimpleUploadedFile(filename, path.read_bytes(), content_type="image/png")
            )
            prepared.append((name, filename, image))

        results = []
        with transaction.atomic():
            for name, filename, (original, mobile, digest) in prepared:
                catalog = CatalogFood.objects.get(display_name=name, status=CatalogFood.STATUS_PUBLISHED)
                food = Food.objects.select_for_update().get(
                    catalog_food_ref=catalog.catalog_ref, name=name, is_global=True, is_active=True,
                )
                asset, created = LegacyFoodVisualAsset.objects.get_or_create(
                    food=food,
                    defaults={
                        "image_data": original,
                        "mobile_image_data": mobile,
                        "content_sha256": digest,
                        "is_published": True,
                        "source_note": f"Aprobación visual Felipe 2026-11-19; {filename}.",
                    },
                )
                if not created and asset.content_sha256 != digest:
                    asset.image_data = original
                    asset.mobile_image_data = mobile
                    asset.content_sha256 = digest
                    asset.is_published = True
                    asset.source_note = f"Aprobación visual Felipe 2026-11-19; {filename}."
                    asset.save(update_fields=[
                        "image_data", "mobile_image_data", "content_sha256",
                        "is_published", "source_note", "updated_at",
                    ])
                elif not created and not asset.is_published:
                    asset.is_published = True
                    asset.save(update_fields=["is_published", "updated_at"])
                results.append((name, food.pk, digest, "created" if created else "current"))
        self.stdout.write(self.style.SUCCESS(f"Approved visuals: {results}"))
