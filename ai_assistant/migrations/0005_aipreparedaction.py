import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai_assistant", "0004_aiusageevent_degraded_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AIPreparedAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("action_key", models.CharField(db_index=True, max_length=100)),
                ("title", models.CharField(max_length=180)),
                ("summary", models.TextField(blank=True)),
                ("target_type", models.CharField(blank=True, max_length=60)),
                ("target_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("target_version", models.CharField(blank=True, max_length=160)),
                ("arguments", models.JSONField(blank=True, default=dict)),
                ("preview", models.JSONField(blank=True, default=dict)),
                ("result", models.JSONField(blank=True, default=dict)),
                ("destructive", models.BooleanField(default=False)),
                ("status", models.CharField(choices=[("prepared", "Prepared"), ("committed", "Committed"), ("cancelled", "Cancelled"), ("expired", "Expired"), ("failed", "Failed")], db_index=True, default="prepared", max_length=20)),
                ("expires_at", models.DateTimeField()),
                ("committed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_prepared_actions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="aipreparedaction",
            index=models.Index(fields=["user", "status", "created_at"], name="ai_prep_user_status_idx"),
        ),
    ]
