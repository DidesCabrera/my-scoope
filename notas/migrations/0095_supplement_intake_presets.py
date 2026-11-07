import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0094_supplement_nutrition"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SupplementIntakePreset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("hour", models.TimeField(blank=True, null=True)),
                ("list_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="supplement_intake_presets", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["list_order", "name", "id"]},
        ),
        migrations.CreateModel(
            name="SupplementIntakePresetItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("supplement_snapshot", models.JSONField(default=dict)),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=9)),
                ("unit", models.CharField(max_length=20)),
                ("order", models.PositiveIntegerField(default=0)),
                ("preset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="notas.supplementintakepreset")),
                ("supplement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="notas.supplement")),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.AddIndex(
            model_name="supplementintakepreset",
            index=models.Index(fields=["created_by", "list_order", "name"], name="supp_preset_user_idx"),
        ),
        migrations.AddIndex(
            model_name="supplementintakepresetitem",
            index=models.Index(fields=["preset", "order"], name="supp_preset_item_idx"),
        ),
    ]
