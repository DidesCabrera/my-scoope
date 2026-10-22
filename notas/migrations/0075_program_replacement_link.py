import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notas", "0074_calendar_progress_period")]

    operations = [
        migrations.AddField(
            model_name="programcalendarization",
            name="replaced_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="replaced_calendarizations",
                to="notas.programcalendarization",
            ),
        ),
        migrations.AddField(
            model_name="programcalendarization",
            name="replacement_effective_on",
            field=models.DateField(blank=True, null=True),
        ),
    ]
