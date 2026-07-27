import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailDeliveryAttempt",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("email_verification", "Email verification"),
                            ("password_reset", "Password reset"),
                            ("share_invitation", "Share invitation"),
                            ("account", "Account"),
                        ],
                        db_index=True,
                        max_length=40,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                            ("suppressed", "Suppressed"),
                            ("rate_limited", "Rate limited"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("recipient_email", models.EmailField(db_index=True, max_length=254)),
                ("subject", models.CharField(blank=True, max_length=255)),
                ("source_model", models.CharField(blank=True, max_length=120)),
                ("source_id", models.CharField(blank=True, max_length=80)),
                (
                    "idempotency_key",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        unique=True,
                    ),
                ),
                ("provider", models.CharField(default="smtp", max_length=40)),
                ("provider_message_id", models.CharField(blank=True, max_length=255)),
                ("reason", models.CharField(blank=True, max_length=80)),
                ("error_code", models.CharField(blank=True, max_length=120)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="email_delivery_attempts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="emaildeliveryattempt",
            index=models.Index(
                fields=["category", "status", "created_at"],
                name="email_category_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="emaildeliveryattempt",
            index=models.Index(
                fields=["actor", "category", "created_at"],
                name="email_actor_category_idx",
            ),
        ),
    ]
