# Generated for OPS06 Admin Operations audit foundation.

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
            name="AdminOperationAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_label", models.CharField(blank=True, max_length=160)),
                ("action", models.CharField(db_index=True, max_length=120)),
                ("source", models.CharField(db_index=True, default="OPS06", max_length=20)),
                ("target_app", models.CharField(db_index=True, max_length=80)),
                ("target_model", models.CharField(db_index=True, max_length=120)),
                ("target_id", models.CharField(db_index=True, max_length=120)),
                ("target_label", models.CharField(blank=True, max_length=220)),
                ("status_before", models.CharField(blank=True, max_length=120)),
                ("status_after", models.CharField(blank=True, max_length=120)),
                ("reason", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="admin_operation_audit_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["target_app", "target_model", "target_id"], name="adm_ops_audit_target_idx"),
                    models.Index(fields=["actor", "created_at"], name="adm_ops_audit_actor_idx"),
                    models.Index(fields=["action", "created_at"], name="adm_ops_audit_action_idx"),
                ],
            },
        ),
    ]
