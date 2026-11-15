"""Persist reviewed editorial copy on the master catalog."""

import json
from pathlib import Path

from django.db import migrations, models

DESCRIPTION_BATCH = Path(__file__).resolve().parents[2] / "food_catalog/data/food_descriptions_v1.json"


def apply_reviewed_descriptions(apps, schema_editor):
    payload = json.loads(DESCRIPTION_BATCH.read_text(encoding="utf-8"))
    if payload["schema_version"] != "myscoope.food_descriptions.v1":
        raise ValueError("Unsupported food description batch")

    catalog_foods = apps.get_model("food_catalog", "CatalogFood")
    database = schema_editor.connection.alias
    for record in payload["records"]:
        if "catalog_ref" not in record or record["review_state"] != "approved":
            continue
        description = record["description"].strip()
        if description:
            catalog_foods.objects.using(database).filter(
                catalog_ref=record["catalog_ref"],
                display_name=record["name"],
                status="published",
                description="",
            ).update(description=description)


class Migration(migrations.Migration):
    dependencies = [("food_catalog", "0021_global_food_visual_refs")]

    operations = [
        migrations.AddField(
            model_name="catalogfood",
            name="description",
            field=models.TextField(
                blank=True,
                help_text="Reviewed editorial description for the food detail; independent of nutritional values.",
            ),
        ),
        migrations.RunPython(apply_reviewed_descriptions, migrations.RunPython.noop),
    ]
