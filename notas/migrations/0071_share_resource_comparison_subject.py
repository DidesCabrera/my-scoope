from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notas", "0070_meal_scope_boundary")]

    operations = [
        migrations.AlterField(
            model_name="shareresource",
            name="subject_type",
            field=models.CharField(
                choices=[
                    ("comparison", "Comparison"),
                    ("daily_plan", "Daily plan"),
                    ("food", "Food"),
                    ("meal", "Meal"),
                    ("program", "Program"),
                ],
                max_length=24,
            ),
        ),
    ]
