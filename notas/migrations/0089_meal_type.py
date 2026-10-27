from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0088_dailyplan_catalog_entry"),
    ]

    operations = [
        migrations.AddField(
            model_name="meal",
            name="meal_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("breakfast", "Desayuno"),
                    ("snack", "Snack"),
                    ("lunch", "Comida"),
                    ("shake", "Batido"),
                    ("dinner", "Cena"),
                ],
                default="",
                max_length=16,
            ),
        ),
    ]
