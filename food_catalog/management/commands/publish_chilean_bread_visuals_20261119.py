"""Attach approved Chilean bread illustrations to every existing catalog record."""

from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from food_catalog.models import CatalogFood, FoodVisualAsset
from food_catalog.visual_assets import prepare_food_visual

ASSETS = (
    Path(__file__).resolve().parents[3]
    / "docs/10_active_cycles/assets/visual_identity_catalog/panes_chile_20261119"
)
APPROVED = (
    ("Marraqueta", "cl-01.png"),
    ("Hallulla", "cl-02.png"),
    ("Pan de molde blanco", "cl-03.png"),
    ("Pan de molde integral", "cl-04.png"),
    ("Pan amasado", "cl-05.png"),
    ("Pan pita blanco", "cl-06.png"),
    ("Pan pita integral", "cl-07.png"),
    ("Pan de centeno", "cl-08.png"),
    ("Pan multigrano", "cl-09.png"),
    ("Baguette", "cl-10.png"),
    ("Ciabatta", "cl-11.png"),
    ("Churrasca", "cl-12.png"),
    ("Dobladita", "cl-13.png"),
    ("Tortilla de rescoldo", "cl-14.png"),
    ("Sopaipilla", "cl-15.png"),
    ("Sopaipilla pasada", "cl-16.png"),
    ("Tortilla mexicana de trigo", "cl-17.png"),
    ("Tortilla de maíz", "cl-18.png"),
)


class Command(BaseCommand):
    help = "Attach the 18 approved bread images to existing catalog records; publish only published foods."

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

        attached = []
        missing = []
        with transaction.atomic():
            for name, filename, (original, mobile, digest) in prepared:
                try:
                    food = CatalogFood.objects.select_for_update().get(display_name=name)
                except CatalogFood.DoesNotExist:
                    missing.append(name)
                    continue
                published = food.status == CatalogFood.STATUS_PUBLISHED
                asset, _ = FoodVisualAsset.objects.update_or_create(
                    food=food,
                    defaults={
                        "image_data": original,
                        "mobile_image_data": mobile,
                        "content_sha256": digest,
                        "is_published": published,
                        "source_note": f"Aprobación visual Felipe 2026-11-19; {filename}.",
                    },
                )
                attached.append((name, food.pk, asset.pk, published, digest))
        self.stdout.write(self.style.SUCCESS(f"Attached {len(attached)} bread visuals: {attached}"))
        self.stdout.write(f"Without catalog record ({len(missing)}): {missing}")
