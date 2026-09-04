import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0053_register_mobile_oauth_client"),
    ]

    operations = [
        migrations.AddField(
            model_name="foodlabelcapturereceipt",
            name="retained_label_image",
            field=models.BinaryField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="foodlabelcapturereceipt",
            name="retained_label_image_content_type",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="foodlabelcapturereceipt",
            name="retained_label_image_sha256",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="foodlabelcapturereceipt",
            name="retained_label_image_size",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="FoodLabelAIAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("idempotency_key", models.CharField(max_length=120)),
                ("request_hash", models.CharField(max_length=64)),
                ("image_sha256", models.CharField(max_length=64)),
                (
                    "status",
                    models.CharField(
                        choices=[("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed")],
                        db_index=True,
                        default="processing",
                        max_length=20,
                    ),
                ),
                ("result_payload", models.JSONField(blank=True, default=dict)),
                ("primary_model", models.CharField(blank=True, max_length=120)),
                ("final_model", models.CharField(blank=True, max_length=120)),
                ("escalated", models.BooleanField(db_index=True, default=False)),
                ("escalation_reason", models.CharField(blank=True, max_length=120)),
                ("provider_call_count", models.PositiveSmallIntegerField(default=0)),
                ("attempt_count", models.PositiveSmallIntegerField(default=1)),
                ("credits_charged", models.PositiveIntegerField(default=0)),
                ("estimated_cost_usd", models.DecimalField(blank=True, decimal_places=6, max_digits=12, null=True)),
                ("error_type", models.CharField(blank=True, max_length=120)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="food_label_ai_analyses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="foodlabelaianalysis",
            constraint=models.UniqueConstraint(
                fields=("user", "idempotency_key"), name="food_label_ai_user_key_unique"
            ),
        ),
        migrations.AddIndex(
            model_name="foodlabelaianalysis",
            index=models.Index(fields=["status", "created_at"], name="food_label_ai_status_idx"),
        ),
        migrations.AddIndex(
            model_name="foodlabelaianalysis",
            index=models.Index(fields=["escalated", "created_at"], name="food_label_ai_escalated_idx"),
        ),
    ]
