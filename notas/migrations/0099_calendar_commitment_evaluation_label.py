from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notas", "0098_calendarcommitment_hour")]

    operations = [
        migrations.AlterField(
            model_name="calendarcommitment",
            name="kind",
            field=models.CharField(
                choices=[
                    ("shopping", "Hacer compras"),
                    ("cooking", "Cocinar"),
                    ("training", "Entrenar"),
                    ("nutritionist", "Evaluación"),
                ],
                max_length=12,
            ),
        ),
    ]
