import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_migrate_legacy_ai_credit_freezes")]

    operations = [
        migrations.CreateModel(
            name="AccountDeletionRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("policy_version", models.CharField(max_length=40)),
                ("source", models.CharField(max_length=40)),
                ("deleted_counts", models.JSONField(blank=True, default=dict)),
                ("retained_counts", models.JSONField(blank=True, default=dict)),
                ("completed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-completed_at", "-id"]},
        ),
    ]
