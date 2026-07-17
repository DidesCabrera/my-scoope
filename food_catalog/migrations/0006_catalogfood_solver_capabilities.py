from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("food_catalog", "0005_catalogcurationcandidate")]

    operations = [
        migrations.AddField(
            model_name="catalogfood",
            name="food_form",
            field=models.CharField(
                choices=[
                    ("unknown", "Unknown"),
                    ("ingredient", "Ingredient"),
                    ("mixed_dish", "Mixed dish"),
                    ("beverage", "Beverage"),
                    ("condiment", "Condiment"),
                ],
                default="unknown",
                help_text="Curated culinary form used by meal grammar after operational snapshot.",
                max_length=30,
            ),
        ),
        migrations.AddField(model_name="catalogfood", name="functional_roles", field=models.JSONField(blank=True, default=list, help_text="Versioned multi-role capability labels; no single role is treated as complete truth.")),
        migrations.AddField(model_name="catalogfood", name="meal_affinities", field=models.JSONField(blank=True, default=list, help_text="Curated meal-kind affinities such as breakfast, snack, main or dinner.")),
        migrations.AddField(model_name="catalogfood", name="dietary_tags", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="catalogfood", name="allergens", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(
            model_name="catalogfood",
            name="preparation_effort",
            field=models.CharField(choices=[("unknown", "Unknown"), ("none", "None"), ("low", "Low"), ("medium", "Medium"), ("high", "High")], default="unknown", max_length=20),
        ),
        migrations.AddField(
            model_name="catalogfood",
            name="cost_band",
            field=models.CharField(choices=[("unknown", "Unknown"), ("low", "Low"), ("medium", "Medium"), ("high", "High")], default="unknown", max_length=20),
        ),
        migrations.AddField(model_name="catalogfood", name="solver_capabilities_version", field=models.CharField(default="solver_food_capabilities.v1", max_length=64)),
        migrations.AddField(model_name="catalogfood", name="solver_feature_confidence", field=models.JSONField(blank=True, default=dict, help_text="Per-feature confidence values from 0 to 100 for solver projections.")),
    ]
