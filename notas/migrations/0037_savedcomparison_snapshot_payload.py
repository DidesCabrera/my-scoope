from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0036_savedcomparison"),
    ]

    operations = [
        migrations.AddField(
            model_name="savedcomparison",
            name="snapshot_payload",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
