from django.conf import settings
from django.core.checks import Error, register


@register()
def calendarization_push_settings_check(app_configs, **kwargs):
    errors = []
    if getattr(settings, "MYSCOOPE_WEB_PUSH_ENABLED", False):
        required = {
            "MYSCOOPE_VAPID_PUBLIC_KEY": getattr(settings, "MYSCOOPE_VAPID_PUBLIC_KEY", ""),
            "MYSCOOPE_VAPID_PRIVATE_KEY": getattr(settings, "MYSCOOPE_VAPID_PRIVATE_KEY", ""),
            "MYSCOOPE_VAPID_SUBJECT": getattr(settings, "MYSCOOPE_VAPID_SUBJECT", ""),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            errors.append(Error(
                "Web Push is enabled but VAPID configuration is incomplete.",
                hint=f"Set: {', '.join(missing)}",
                id="notas.E001",
            ))

    if getattr(settings, "MYSCOOPE_APNS_ENABLED", False):
        required = {
            "MYSCOOPE_APNS_KEY_ID": getattr(settings, "MYSCOOPE_APNS_KEY_ID", ""),
            "MYSCOOPE_APNS_TEAM_ID": getattr(settings, "MYSCOOPE_APNS_TEAM_ID", ""),
            "MYSCOOPE_APNS_PRIVATE_KEY": getattr(settings, "MYSCOOPE_APNS_PRIVATE_KEY", ""),
            "MYSCOOPE_APNS_BUNDLE_ID": getattr(settings, "MYSCOOPE_APNS_BUNDLE_ID", ""),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            errors.append(Error(
                "APNs is enabled but provider configuration is incomplete.",
                hint=f"Set: {', '.join(missing)}",
                id="notas.E002",
            ))
    return errors
