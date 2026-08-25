from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0051_profile_mobile_disclosure"),
    ]

    operations = [
        migrations.AlterField(
            model_name="calendarizedmealexecution",
            name="action",
            field=models.CharField(
                choices=[
                    ("completed", "Completed"),
                    ("skipped", "Skipped"),
                    ("reset", "Reset"),
                    ("note", "Note"),
                ],
                max_length=20,
            ),
        ),
    ]
