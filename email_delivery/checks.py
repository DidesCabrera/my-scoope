import os

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security, deploy=True)
def email_abuse_protection_checks(app_configs, **kwargs):
    findings = []
    production = os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(".prod")

    if settings.TURNSTILE_ENABLED and (
        not settings.TURNSTILE_SITE_KEY or not settings.TURNSTILE_SECRET_KEY
    ):
        findings.append(
            Error(
                "Turnstile is enabled without both required keys.",
                hint="Configure TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY.",
                id="email_delivery.E001",
            )
        )
    if production and not settings.TURNSTILE_ENABLED:
        findings.append(
            Warning(
                "Public signup is running without Turnstile.",
                hint="Configure Turnstile and set TURNSTILE_ENABLED=true.",
                id="email_delivery.W001",
            )
        )
    if production and not settings.CACHE_URL:
        findings.append(
            Warning(
                "Rate limits are using process-local memory.",
                hint="Provision Render Key Value and configure CACHE_URL.",
                id="email_delivery.W002",
            )
        )
    if production and settings.ACCOUNT_EMAIL_VERIFICATION != "mandatory":
        findings.append(
            Warning(
                "Production account email verification is not mandatory.",
                hint="Set ACCOUNT_EMAIL_VERIFICATION=mandatory.",
                id="email_delivery.W003",
            )
        )
    return findings
