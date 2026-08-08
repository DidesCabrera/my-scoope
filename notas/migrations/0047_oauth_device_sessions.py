import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0046_nutritionistmemberrelationship_proxy"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OAuthDeviceSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("device_id_hash", models.CharField(max_length=64)),
                ("device_name", models.CharField(blank=True, max_length=120)),
                ("platform", models.CharField(choices=[("ios", "iOS"), ("android", "Android"), ("web", "Web")], max_length=20)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="device_sessions", to="notas.oauthclient")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="oauth_device_sessions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-updated_at", "-id"],
                "indexes": [models.Index(fields=["user", "is_active", "updated_at"], name="oauth_device_user_active_idx")],
                "constraints": [models.UniqueConstraint(fields=("client", "user", "device_id_hash"), name="oauth_device_client_user_hash_uniq")],
            },
        ),
        migrations.AddField(
            model_name="mcpusertoken",
            name="device_session",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="access_tokens", to="notas.oauthdevicesession"),
        ),
        migrations.CreateModel(
            name="OAuthRefreshToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("family_id", models.UUIDField(db_index=True, default=uuid.uuid4)),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("scopes", models.JSONField(default=list)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("rotated_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("replaced_by", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="replaces", to="notas.oauthrefreshtoken")),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="refresh_tokens", to="notas.oauthdevicesession")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [models.Index(fields=["session", "family_id", "created_at"], name="oauth_refresh_sess_family_idx")],
            },
        ),
    ]
