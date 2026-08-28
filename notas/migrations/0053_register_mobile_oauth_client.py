from django.db import migrations

MOBILE_CLIENT_ID = "myscoope-ios"
MOBILE_CLIENT_NAME = "My Scoope iOS"
MOBILE_REDIRECT_URI = "myscoope://oauth/callback"
MOBILE_SCOPES = ["mobile:read", "mobile:write", "mobile:account"]


def register_mobile_oauth_client(apps, schema_editor):
    OAuthClient = apps.get_model("notas", "OAuthClient")
    client, created = OAuthClient.objects.get_or_create(
        client_id=MOBILE_CLIENT_ID,
        defaults={
            "client_name": MOBILE_CLIENT_NAME,
            "redirect_uris": [MOBILE_REDIRECT_URI],
            "allowed_scopes": MOBILE_SCOPES,
            "is_active": True,
        },
    )

    if created:
        return

    update_fields = []

    redirect_uris = list(client.redirect_uris or [])
    if MOBILE_REDIRECT_URI not in redirect_uris:
        client.redirect_uris = [*redirect_uris, MOBILE_REDIRECT_URI]
        update_fields.append("redirect_uris")

    allowed_scopes = list(client.allowed_scopes or [])
    missing_scopes = [scope for scope in MOBILE_SCOPES if scope not in allowed_scopes]
    if missing_scopes:
        client.allowed_scopes = [*allowed_scopes, *missing_scopes]
        update_fields.append("allowed_scopes")

    if update_fields:
        client.save(update_fields=[*update_fields, "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0052_alter_calendarizedmealexecution_action"),
    ]

    operations = [
        migrations.RunPython(register_mobile_oauth_client, migrations.RunPython.noop),
    ]
