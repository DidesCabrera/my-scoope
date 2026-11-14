import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("food_catalog", "0018_foodvisualasset"),
        ("notas", "0100_supplement_catalog"),
    ]

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
    ]
