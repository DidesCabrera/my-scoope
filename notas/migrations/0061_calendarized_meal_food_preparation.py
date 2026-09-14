from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notas", "0060_backfill_all_legacy_shares")]

    operations = [
        migrations.AddField(
            model_name="calendarizedmealexecution",
            name="food_snapshot_key",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AlterField(
            model_name="calendarizedmealexecution",
            name="action",
            field=models.CharField(
                choices=[
                    ("completed", "Completed"),
                    ("skipped", "Skipped"),
                    ("reset", "Reset"),
                    ("note", "Note"),
                    ("food_prepared", "Food prepared"),
                    ("food_unprepared", "Food unprepared"),
                ],
                max_length=20,
            ),
        ),
    ]
