"""Copy master descriptions to operational foods and attach limited legacy copy."""

import json
from pathlib import Path

from django.db import migrations, models

DESCRIPTION_BATCH = Path(__file__).resolve().parents[2] / "food_catalog/data/food_descriptions_v1.json"


def apply_reviewed_descriptions(apps, schema_editor):
    payload = json.loads(DESCRIPTION_BATCH.read_text(encoding="utf-8"))
    if payload["schema_version"] != "myscoope.food_descriptions.v1":
        raise ValueError("Unsupported food description batch")

    catalog_foods = apps.get_model("food_catalog", "CatalogFood")
    foods = apps.get_model("notas", "Food")
    database = schema_editor.connection.alias
    for catalog_food in catalog_foods.objects.using(database).filter(status="published").exclude(description="").iterator():
        foods.objects.using(database).filter(
            catalog_food_ref=catalog_food.catalog_ref,
            name=catalog_food.display_name,
            is_global=True,
            is_active=True,
            visibility__in=["core", "extended"],
            description="",
        ).update(description=catalog_food.description)

    for record in payload["records"]:
        if "operational_food_id" not in record or record["review_state"] != "approved_with_limitations":
            continue
        description = record["description"].strip()
        if not description:
            continue
        foods.objects.using(database).filter(
            pk=record["operational_food_id"],
            name=record["name"],
            catalog_food_ref__isnull=True,
            is_global=True,
            is_active=True,
            is_verified=False,
            visibility__in=["core", "extended"],
            description="",
        ).update(description=description)


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0100_supplement_catalog"),
        ("food_catalog", "0022_catalogfood_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="food",
            name="description",
            field=models.TextField(
                blank=True,
                help_text="Editorial description copied from Food Catalog or approved for this operational food.",
            ),
        ),
        migrations.RunPython(apply_reviewed_descriptions, migrations.RunPython.noop),
    ]
