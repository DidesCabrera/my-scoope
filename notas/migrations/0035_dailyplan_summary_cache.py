# Generated for DailyPlan persistent summary cache.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0034_program_summary_cache"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailyplan",
            name="summary_cache",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="dailyplan",
            name="summary_cache_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
