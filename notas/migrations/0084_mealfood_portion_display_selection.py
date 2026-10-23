from django.db import migrations, models


def backfill_metric_display_selection(apps, schema_editor):
    MealFood = apps.get_model("notas", "MealFood")
    rows = list(MealFood.objects.select_related("food").all())
    for row in rows:
        row.portion_display_quantity = row.quantity
        row.portion_display_measure = row.food.portion_unit
    if rows:
        MealFood.objects.bulk_update(
            rows,
            ["portion_display_quantity", "portion_display_measure"],
            batch_size=500,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0083_apply_myscoope_food_portions_v1"),
    ]

    operations = [
        migrations.AddField(
            model_name="mealfood",
            name="portion_display_quantity",
            field=models.FloatField(
                blank=True,
                help_text="Quantity exactly as selected by the user before metric conversion.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="mealfood",
            name="portion_display_measure",
            field=models.CharField(
                blank=True,
                help_text="Household measure or metric unit selected by the user.",
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_metric_display_selection, migrations.RunPython.noop),
    ]
