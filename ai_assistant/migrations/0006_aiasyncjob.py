import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai_assistant", "0005_aipreparedaction"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AIAsyncJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("kind", models.CharField(db_index=True, max_length=80)),
                ("idempotency_key", models.CharField(max_length=120)),
                ("lane_key", models.CharField(blank=True, db_index=True, help_text="Serializes related jobs such as turns in one conversation.", max_length=160)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("retrying", "Retrying"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("cancelled", "Cancelled")], db_index=True, default="queued", max_length=20)),
                ("request_payload", models.JSONField(default=dict)),
                ("result_payload", models.JSONField(blank=True, default=dict)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("max_attempts", models.PositiveSmallIntegerField(default=3)),
                ("available_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("leased_at", models.DateTimeField(blank=True, null=True)),
                ("lease_expires_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("error_code", models.CharField(blank=True, max_length=120)),
                ("error_message", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_async_jobs", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["created_at", "id"],
                "indexes": [models.Index(fields=["status", "available_at"], name="ai_job_status_available_idx"), models.Index(fields=["user", "status", "created_at"], name="ai_job_user_status_created_idx")],
                "constraints": [models.UniqueConstraint(fields=("user", "kind", "idempotency_key"), name="ai_job_user_kind_idempotency_unique")],
            },
        ),
    ]
