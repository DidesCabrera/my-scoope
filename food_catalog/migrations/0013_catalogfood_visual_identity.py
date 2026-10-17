from django.db import migrations, models


def populate_catalog_food_visuals(apps, schema_editor):
    from core.food_visual_identity import infer_food_visual_identity

    CatalogFood = apps.get_model("food_catalog", "CatalogFood")
    pending = []
    for food in CatalogFood.objects.all().iterator():
        visual = infer_food_visual_identity(
            food.display_name,
            food_group=food.food_group,
            food_subgroup=food.food_subgroup,
        )
        food.emoji = visual.emoji
        food.visual_key = visual.visual_key
        pending.append(food)
        if len(pending) >= 500:
            CatalogFood.objects.bulk_update(pending, ["emoji", "visual_key"])
            pending.clear()
    if pending:
        CatalogFood.objects.bulk_update(pending, ["emoji", "visual_key"])


class Migration(migrations.Migration):
    dependencies = [("food_catalog", "0012_catalogfood_portion_unit")]

    operations = [
        migrations.AddField(
            model_name="catalogfood",
            name="emoji",
            field=models.CharField(
                blank=True,
                help_text="Optional Unicode emoji displayed beside the food name.",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="catalogfood",
            name="visual_key",
            field=models.CharField(
                blank=True,
                help_text="Stable semantic key for a future My Scoope custom food icon.",
                max_length=64,
            ),
        ),
        migrations.RunPython(populate_catalog_food_visuals, migrations.RunPython.noop),
    ]
