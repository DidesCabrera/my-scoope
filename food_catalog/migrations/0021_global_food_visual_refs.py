"""Give existing global food images a stable, mobile-compatible public URL."""

import uuid

from django.conf import settings
from django.db import migrations, models

NOTAS_INSTALLED = any(app == "notas" or app.startswith("notas.apps.") for app in settings.INSTALLED_APPS)


def assign_public_refs(apps, schema_editor):
    Asset = apps.get_model("food_catalog", "LegacyFoodVisualAsset")
    for asset in Asset.objects.using(schema_editor.connection.alias).filter(public_ref__isnull=True).iterator():
        asset.public_ref = uuid.uuid4()
        asset.save(update_fields=["public_ref"])


class Migration(migrations.Migration):
    dependencies = [("food_catalog", "0020_seed_legacy_scoop_visuals")]

    operations = [
        migrations.AddField(
            model_name="legacyfoodvisualasset",
            name="public_ref",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(assign_public_refs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="legacyfoodvisualasset",
            name="public_ref",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterModelOptions(
            name="legacyfoodvisualasset",
            options={
                "verbose_name": "imagen de alimento global",
                "verbose_name_plural": "imágenes de alimentos globales",
            },
        ),
    ] if NOTAS_INSTALLED else []
