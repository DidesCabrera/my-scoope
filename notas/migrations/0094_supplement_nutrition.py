from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0093_supplements"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplement",
            name="nutrition",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
