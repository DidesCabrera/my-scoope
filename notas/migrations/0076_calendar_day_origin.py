import django.db.models.deletion
from django.db import migrations, models


def backfill_origin_calendarization(apps, schema_editor):
    Day = apps.get_model("notas", "CalendarizedDay")
    for day in Day.objects.filter(calendarization__isnull=False).iterator(chunk_size=500):
        day.origin_calendarization_id = day.calendarization_id
        day.save(update_fields=["origin_calendarization"])


class Migration(migrations.Migration):
    dependencies = [("notas", "0075_program_replacement_link")]

    operations = [
        migrations.AddField(
            model_name="calendarizedday",
            name="origin_calendarization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="originated_days",
                to="notas.programcalendarization",
            ),
        ),
        migrations.RunPython(backfill_origin_calendarization, migrations.RunPython.noop),
    ]
