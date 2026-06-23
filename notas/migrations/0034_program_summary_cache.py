# Generated for Program persistent summary cache.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0033_programshare_alter_program_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="program",
            name="summary_cache",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="program",
            name="summary_cache_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
