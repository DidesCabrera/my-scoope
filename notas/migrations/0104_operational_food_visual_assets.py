import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0103_food_label_capture_curation"),
        ("food_catalog", "0024_transfer_operational_visual_assets"),
    ]

    # The table and foreign key were created by food_catalog. This changes
    # Django ownership without recreating the table or touching image bytes.
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="LegacyFoodVisualAsset",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("public_ref", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                        ("image_data", models.BinaryField(editable=False)),
                        ("mobile_image_data", models.BinaryField(editable=False)),
                        ("content_sha256", models.CharField(max_length=64, editable=False)),
                        ("is_published", models.BooleanField(default=False)),
                        ("source_note", models.CharField(max_length=255, blank=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("food", models.OneToOneField(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name="legacy_visual_asset",
                            to="notas.food",
                        )),
                    ],
                    options={
                        "db_table": "food_catalog_legacyfoodvisualasset",
                        "verbose_name": "imagen de alimento global",
                        "verbose_name_plural": "imágenes de alimentos globales",
                    },
                ),
            ],
        ),
    ]
