"""Assign approved food and preparation visuals to the production consumer catalog."""

from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from food_catalog.models import CatalogFood, CatalogPreparation, FoodVisualAsset, PreparationVisualAsset
from food_catalog.visual_assets import prepare_food_visual
from notas.domain.models import Food, LegacyFoodVisualAsset, Preparation

ASSETS = Path(__file__).resolve().parents[3] / "docs/10_active_cycles/assets/visual_identity_catalog"
FOODS = (
    ("Ají verde crudo", "green-chili-raw-approved.png"),
    ("Aceite de maravilla", "sunflower-oil-bottle-approved.png"),
    ("Aceite de coco", "coconut-oil-jar-approved.png"),
)


def _image(filename):
    path = ASSETS / filename
    if not path.is_file():
        raise CommandError(f"Approved image missing: {path}")
    return prepare_food_visual(SimpleUploadedFile(filename, path.read_bytes(), content_type="image/png"))


def _publish(model, identity_field, identity, filename, note):
    original, mobile, digest = _image(filename)
    existing = model.objects.filter(**{identity_field: identity}).first()
    if existing:
        if existing.content_sha256 != digest:
            raise CommandError(f"Different image already assigned to {identity}: {existing.pk}")
        if not existing.is_published:
            existing.is_published = True
            existing.source_note = note
            existing.save(update_fields=["is_published", "source_note", "updated_at"])
        return existing, "already assigned"
    asset = model.objects.create(
        **{identity_field: identity}, image_data=original, mobile_image_data=mobile,
        content_sha256=digest, is_published=True, source_note=note,
    )
    return asset, "published"


class Command(BaseCommand):
    help = "Publish approved illustrations for cacao, ají, oils and Completo italiano. Consumer only."

    def handle(self, *args, **options):
        results = []
        with transaction.atomic():
            cacao = Food.objects.select_for_update().get(name="Cacao", is_global=True, is_active=True)
            if cacao.catalog_food_id is not None:
                raise CommandError("Cacao identity changed; review before publication")
            asset, state = _publish(
                LegacyFoodVisualAsset, "food", cacao, "cacao-beans-approved.png",
                "Aprobación visual Felipe 2026-11-15 y confirmación 2026-11-17; cacao-beans-approved.png.",
            )
            results.append((cacao.name, cacao.pk, asset.pk, state))

            for name, filename in FOODS:
                catalog = CatalogFood.objects.select_for_update().get(display_name=name, status=CatalogFood.STATUS_PUBLISHED)
                food = Food.objects.get(
                    catalog_food_ref=catalog.catalog_ref, is_global=True, is_active=True,
                )
                if food.name != name:
                    raise CommandError(f"Unexpected operational identity for {name}: {food.name}")
                asset, state = _publish(
                    FoodVisualAsset, "food", catalog, filename,
                    f"Aprobación visual Felipe 2026-11-15/17; {filename}.",
                )
                results.append((name, food.pk, asset.pk, state))

            catalog_preparation = CatalogPreparation.objects.select_for_update().get(
                display_name="Completo italiano", is_active=True,
                current_version__published_at__isnull=False,
            )
            preparation = Preparation.objects.get(
                catalog_ref=catalog_preparation.catalog_ref,
                name="Completo italiano", is_global=True, is_active=True,
                current_version__isnull=False,
            )
            asset, state = _publish(
                PreparationVisualAsset, "preparation", catalog_preparation,
                "completo-italiano-preparation-proposal.png",
                "Aprobación visual Felipe 2026-11-15; completo-italiano-preparation-proposal.png.",
            )
            results.append((preparation.name, preparation.pk, asset.pk, state))
        self.stdout.write(self.style.SUCCESS(f"Approved visuals: {results}"))
