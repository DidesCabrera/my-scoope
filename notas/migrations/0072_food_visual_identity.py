from django.db import migrations, models


def populate_operational_food_visuals(apps, schema_editor):
    from core.food_visual_identity import infer_food_visual_identity

    Food = apps.get_model("notas", "Food")
    pending = []
    for food in Food.objects.all().iterator():
        visual = infer_food_visual_identity(
            food.name,
            food_group=food.food_group,
            food_subgroup=food.food_subgroup,
        )
        food.emoji = visual.emoji
        food.visual_key = visual.visual_key
        pending.append(food)
        if len(pending) >= 500:
            Food.objects.bulk_update(pending, ["emoji", "visual_key"])
            pending.clear()
    if pending:
        Food.objects.bulk_update(pending, ["emoji", "visual_key"])


class Migration(migrations.Migration):
    dependencies = [("notas", "0071_share_resource_comparison_subject")]

    operations = [
        migrations.AddField(
            model_name="food",
            name="emoji",
            field=models.CharField(
                blank=True,
                help_text="Optional visual copied from the Food Catalog or inferred for user foods.",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="food",
            name="visual_key",
            field=models.CharField(
                blank=True,
                help_text="Stable semantic key for a future My Scoope custom food icon.",
                max_length=64,
            ),
        ),
        migrations.RunPython(populate_operational_food_visuals, migrations.RunPython.noop),
    ]
