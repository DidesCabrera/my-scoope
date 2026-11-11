from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0097_preparation_preparationversion_preparationingredient_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="calendarcommitment",
            name="hour",
            field=models.TimeField(blank=True, null=True),
        ),
    ]
