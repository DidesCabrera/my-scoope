from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


def backfill_calendar_day_ownership(apps, schema_editor):
    Day = apps.get_model("notas", "CalendarizedDay")
    Execution = apps.get_model("notas", "CalendarizedMealExecution")
    executed_ids = set(Execution.objects.values_list("calendarized_day_id", flat=True).distinct())
    days = list(Day.objects.select_related("calendarization").order_by("user_id", "calendar_date", "created_at", "id"))
    candidates = {}
    for day in days:
        calendarization = day.calendarization
        day.user_id = calendarization.user_id
        if not day.plan_snapshot:
            day.assignment_state = "empty"
            continue
        if calendarization.status == "cancelled":
            cancelled_at = calendarization.cancelled_at
            try:
                zone = ZoneInfo(calendarization.timezone_name)
            except (ZoneInfoNotFoundError, ValueError):
                zone = ZoneInfo("UTC")
            if cancelled_at and day.calendar_date >= cancelled_at.astimezone(zone).date() and day.id not in executed_ids:
                day.assignment_state = "superseded"
                day.change_reason = "legacy_calendarization_cancelled"
                continue
        candidates.setdefault((day.user_id, day.calendar_date), []).append(day)

    for same_date in candidates.values():
        # Existing data can contain overlapping former programs. The latest
        # assignment with execution is the visible slot. Without execution,
        # the latest snapshot wins. Earlier snapshots remain intact.
        same_date.sort(key=lambda day: (day.id in executed_ids, day.created_at, day.id))
        for day in same_date[:-1]:
            day.assignment_state = "superseded"
            day.change_reason = "legacy_date_overlap"

    Day.objects.bulk_update(days, ["user", "assignment_state", "change_reason"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0072_food_visual_identity"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="calendarizedday",
            name="calendarization",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="days", to="notas.programcalendarization"),
        ),
        migrations.AlterField(
            model_name="calendarizedday",
            name="day_number",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="calendarizedday",
            name="week_number",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="calendarizedday",
            name="user",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="calendarized_days", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="calendarizedday",
            name="source_kind",
            field=models.CharField(choices=[("program", "Program"), ("manual", "Manual")], default="program", max_length=12),
        ),
        migrations.AddField(
            model_name="calendarizedday",
            name="assignment_state",
            field=models.CharField(choices=[("current", "Current"), ("empty", "Empty"), ("superseded", "Superseded"), ("removed", "Removed")], default="current", max_length=12),
        ),
        migrations.AddField(
            model_name="calendarizedday",
            name="superseded_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="superseded_days", to="notas.calendarizedday"),
        ),
        migrations.AddField(
            model_name="calendarizedday",
            name="state_changed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="calendarizedday",
            name="change_reason",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="calendarizedday",
            name="assignment_key",
            field=models.CharField(blank=True, max_length=120, null=True, unique=True),
        ),
        migrations.RunPython(backfill_calendar_day_ownership, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="calendarizedday",
            constraint=models.UniqueConstraint(condition=Q(assignment_state="current", user__isnull=False), fields=("user", "calendar_date"), name="cal_one_current_plan_per_date"),
        ),
        migrations.AddIndex(
            model_name="calendarizedday",
            index=models.Index(fields=["user", "calendar_date", "assignment_state"], name="cal_user_date_state_idx"),
        ),
    ]
