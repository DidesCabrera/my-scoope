import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0076_calendar_day_origin"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CalendarCommitment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("calendar_date", models.DateField()),
                ("kind", models.CharField(choices=[("shopping", "Hacer compras"), ("cooking", "Cocinar"), ("training", "Entrenar")], max_length=12)),
                ("note", models.CharField(blank=True, max_length=500)),
                ("food_period_start", models.DateField(blank=True, null=True)),
                ("food_period_end", models.DateField(blank=True, null=True)),
                ("food_plans_count", models.PositiveIntegerField(default=0)),
                ("foods_snapshot", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="calendar_commitments", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["calendar_date", "kind", "id"],
                "indexes": [models.Index(fields=["user", "calendar_date"], name="cal_commitment_user_date_idx")],
                "constraints": [models.UniqueConstraint(fields=("user", "calendar_date", "kind"), name="cal_unique_commitment_kind_date")],
            },
        ),
    ]
