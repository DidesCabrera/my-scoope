import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0073_calendar_day_assignment_foundation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CalendarProgressPeriod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("starts_on", models.DateField()),
                ("ends_on", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="calendar_progress_periods", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-starts_on", "-id"],
                "constraints": [
                    models.UniqueConstraint(condition=Q(ends_on__isnull=True), fields=("user",), name="cal_one_open_progress_period"),
                    models.CheckConstraint(condition=Q(ends_on__isnull=True) | Q(ends_on__gte=models.F("starts_on")), name="cal_progress_period_valid_range"),
                ],
                "indexes": [models.Index(fields=["user", "starts_on"], name="cal_progress_user_start_idx")],
            },
        ),
    ]
