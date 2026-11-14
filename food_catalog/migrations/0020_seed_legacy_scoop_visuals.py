"""Publish the four user-approved scoop visuals on their verified legacy foods."""

from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import migrations

from food_catalog.visual_assets import prepare_food_visual


APPROVED_FOODS = (
    (1, "Dextrosa", "dextrosa.png"),
    (7, "Maca Andina", "maca_andina.png"),
    (29, "Colageno Hidrolizado", "colageno_hidrolizado.png"),
    (30, "Whey Protein", "whey_protein.png"),
)
SOURCE_NOTE = "Ilustración My Scoope aprobada por Felipe el 2026-11-14; lote de scoops."


def publish_approved_visuals(apps, schema_editor):
    Food = apps.get_model("notas", "Food")
    Asset = apps.get_model("food_catalog", "LegacyFoodVisualAsset")
    source_dir = Path(__file__).resolve().parent.parent / "data" / "legacy_visuals"
    database = schema_editor.connection.alias

    for food_id, expected_name, filename in APPROVED_FOODS:
        food = Food.objects.using(database).filter(pk=food_id).first()
        # Staging and test databases can have other IDs; never attach by ID alone.
        if food is None or food.name != expected_name:
            continue
        if not food.is_global or not food.is_active or food.catalog_food_ref:
            continue
        raw = (source_dir / filename).read_bytes()
        upload = SimpleUploadedFile(filename, raw, content_type="image/png")
        original, mobile, digest = prepare_food_visual(upload)
        Asset.objects.using(database).update_or_create(
            food_id=food_id,
            defaults={
                "image_data": original,
                "mobile_image_data": mobile,
                "content_sha256": digest,
                "is_published": True,
                "source_note": SOURCE_NOTE,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("food_catalog", "0019_legacyfoodvisualasset")]

    operations = [migrations.RunPython(publish_approved_visuals, migrations.RunPython.noop)]
