import json
from decimal import Decimal
from pathlib import Path

from django.db import migrations


def apply_curated_portions(apps, schema_editor):
    Food = apps.get_model("notas", "Food")
    FoodPortion = apps.get_model("notas", "FoodPortion")
    database = schema_editor.connection.alias
    data_path = (
        Path(__file__).resolve().parents[2]
        / "food_catalog"
        / "data"
        / "myscoope_food_portions_v1.json"
    )
    rows = json.loads(data_path.read_text(encoding="utf-8"))["foods"]

    for row in rows:
        food = (
            Food.objects.using(database)
            .filter(is_global=True, catalog_food_ref=row["catalog_ref"])
            .first()
        )
        if food is None:
            continue
        metric_amount = Decimal(row["metric_amount"])
        Food.objects.using(database).filter(pk=food.pk).update(
            myscoope_group=row["myscoope_group"],
            portion_unit=row["metric_unit"],
            default_portion_g=metric_amount,
        )
        portion = (
            FoodPortion.objects.using(database)
            .filter(food_id=food.pk, is_default=True)
            .order_by("id")
            .first()
        )
        if portion is None:
            continue
        FoodPortion.objects.using(database).filter(pk=portion.pk).update(
            grams=metric_amount,
            household_amount=Decimal(row["household_amount"]),
            household_measure=row["household_measure"],
            household_detail=row["household_detail"],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("food_catalog", "0016_apply_myscoope_food_portions_v1"),
        ("notas", "0082_food_myscoope_group_and_household_portions"),
    ]

    operations = [
        migrations.RunPython(apply_curated_portions, migrations.RunPython.noop),
    ]
