from django.conf import settings


def turnstile(request):
    return {
        "turnstile_enabled": getattr(settings, "TURNSTILE_ENABLED", False),
        "turnstile_site_key": getattr(settings, "TURNSTILE_SITE_KEY", ""),
        "turnstile_action": getattr(
            settings,
            "TURNSTILE_EXPECTED_ACTION",
            "signup",
        ),
    }
