from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("notas", "0077_calendar_commitment")]

    operations = [
        migrations.AlterField(
            model_name="calendarcommitment",
            name="kind",
            field=models.CharField(
                choices=[
                    ("shopping", "Hacer compras"),
                    ("cooking", "Cocinar"),
                    ("training", "Entrenar"),
                    ("nutritionist", "Cita nutricionista"),
                ],
                max_length=12,
            ),
        ),
    ]
