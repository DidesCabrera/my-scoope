import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("food_catalog", "0006_catalogfood_solver_capabilities"),
    ]

    operations = [
        migrations.AddField(
            model_name="catalogimportbatch",
            name="dry_run_batch",
            field=models.ForeignKey(
                blank=True,
                help_text="Completed equivalent dry-run that authorized this mutating batch.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="applied_batches",
                to="food_catalog.catalogimportbatch",
            ),
        ),
        migrations.AddField(
            model_name="catalogimportbatch",
            name="input_sha256",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="catalogimportbatch",
            name="parameters_payload",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="catalogimportbatch",
            name="reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="catalogimportbatch",
            name="requested_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="requested_catalog_import_batches",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
