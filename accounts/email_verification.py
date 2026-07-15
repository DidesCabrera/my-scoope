from __future__ import annotations


SMTP_EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


def smtp_email_is_configured(email_backend: str, email_host: str) -> bool:
    return str(email_backend or "").strip() == SMTP_EMAIL_BACKEND and bool(
        str(email_host or "").strip()
    )


def production_email_verification_default(email_backend: str, email_host: str) -> str:
    if smtp_email_is_configured(email_backend, email_host):
        return "mandatory"
    return "none"
