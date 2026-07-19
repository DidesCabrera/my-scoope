from django.conf import settings
from django.core.checks import Error, register


@register()
def calendarization_push_settings_check(app_configs, **kwargs):
    if not getattr(settings, "MYSCOOPE_WEB_PUSH_ENABLED", False):
        return []
    required = {
        "MYSCOOPE_VAPID_PUBLIC_KEY": getattr(settings, "MYSCOOPE_VAPID_PUBLIC_KEY", ""),
        "MYSCOOPE_VAPID_PRIVATE_KEY": getattr(settings, "MYSCOOPE_VAPID_PRIVATE_KEY", ""),
        "MYSCOOPE_VAPID_SUBJECT": getattr(settings, "MYSCOOPE_VAPID_SUBJECT", ""),
    }
    missing = [name for name, value in required.items() if not value]
    if not missing:
        return []
    return [
        Error(
            "Web Push is enabled but VAPID configuration is incomplete.",
            hint=f"Set: {', '.join(missing)}",
            id="notas.E001",
        )
    ]
