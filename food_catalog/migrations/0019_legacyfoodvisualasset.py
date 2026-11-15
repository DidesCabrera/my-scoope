import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

NOTAS_INSTALLED = any(app == "notas" or app.startswith("notas.apps.") for app in settings.INSTALLED_APPS)


class Migration(migrations.Migration):
    # The authority deploys food_catalog without the operational notas app.
    # Keep the historical migration identity, but only create this operational
    # table in consumer databases where its Food dependency exists.
    dependencies = [("food_catalog", "0018_foodvisualasset")]
    if NOTAS_INSTALLED:
        dependencies.append(("notas", "0100_supplement_catalog"))

    operations = [
        migrations.CreateModel(
            name="LegacyFoodVisualAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image_data", models.BinaryField(editable=False)),
                ("mobile_image_data", models.BinaryField(editable=False)),
                ("content_sha256", models.CharField(editable=False, max_length=64)),
                ("is_published", models.BooleanField(default=False)),
                ("source_note", models.CharField(blank=True, max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("food", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="legacy_visual_asset", to="notas.food")),
            ],
        ),
    ] if NOTAS_INSTALLED else []
