import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("notas", "0061_calendarized_meal_food_preparation"),
    ]

    operations = [
        migrations.CreateModel(
            name="PinnedDailyPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("dailyplan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pinned_by", to="notas.dailyplan")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="pinned_dailyplan", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="PinnedDailyPlanMealExecution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("local_date", models.DateField()),
                ("meal_key", models.CharField(max_length=80)),
                ("action", models.CharField(choices=[("completed", "Completed"), ("skipped", "Skipped"), ("reset", "Reset"), ("note", "Note"), ("food_prepared", "Food prepared"), ("food_unprepared", "Food unprepared")], max_length=20)),
                ("idempotency_key", models.CharField(max_length=120, unique=True)),
                ("note", models.CharField(blank=True, max_length=500)),
                ("food_key", models.CharField(blank=True, max_length=80)),
                ("occurred_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("pinned_dailyplan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="meal_execution_events", to="notas.pinneddailyplan")),
            ],
            options={
                "ordering": ["created_at", "id"],
                "indexes": [models.Index(fields=["pinned_dailyplan", "local_date", "created_at"], name="pin_plan_exec_day_idx")],
            },
        ),
    ]
