from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai_assistant", "0003_ai_credits"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aiusageevent",
            name="status",
            field=models.CharField(
                choices=[
                    ("completed", "Completed"),
                    ("degraded", "Degraded"),
                    ("error", "Error"),
                    ("blocked", "Blocked"),
                ],
                db_index=True,
                default="completed",
                max_length=20,
            ),
        ),
    ]
