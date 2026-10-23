import json
from decimal import Decimal
from pathlib import Path

from django.db import migrations


def apply_curated_portions(apps, schema_editor):
    CatalogFood = apps.get_model("food_catalog", "CatalogFood")
    CatalogFoodPortion = apps.get_model("food_catalog", "CatalogFoodPortion")
    database = schema_editor.connection.alias
    data_path = Path(__file__).resolve().parents[1] / "data" / "myscoope_food_portions_v1.json"
    rows = json.loads(data_path.read_text(encoding="utf-8"))["foods"]

    for row in rows:
        food = (
            CatalogFood.objects.using(database)
            .filter(catalog_ref=row["catalog_ref"])
            .first()
        )
        if food is None:
            continue
        CatalogFood.objects.using(database).filter(pk=food.pk).update(
            myscoope_group=row["myscoope_group"],
            portion_unit=row["metric_unit"],
        )
        portion = (
            CatalogFoodPortion.objects.using(database)
            .filter(catalog_food_id=food.pk, is_default=True)
            .order_by("id")
            .first()
        )
        if portion is None:
            continue
        CatalogFoodPortion.objects.using(database).filter(pk=portion.pk).update(
            grams=Decimal(row["metric_amount"]),
            household_amount=Decimal(row["household_amount"]),
            household_measure=row["household_measure"],
            household_detail=row["household_detail"],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("food_catalog", "0015_myscoope_group_and_household_portions"),
    ]

    operations = [
        migrations.RunPython(apply_curated_portions, migrations.RunPython.noop),
    ]
