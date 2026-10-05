import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("billing", "0007_product_scoped_base_plan_ids"),
    ]

    operations = [
        migrations.CreateModel(
            name="AppleSandboxAccess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "purpose",
                    models.CharField(
                        choices=[("internal", "Internal testing"), ("app_review", "App Review")],
                        max_length=24,
                    ),
                ),
                ("active", models.BooleanField(db_index=True, default=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="apple_sandbox_access",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["user_id"]},
        ),
    ]
