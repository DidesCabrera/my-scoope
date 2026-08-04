from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


@dataclass(frozen=True)
class TurnstileValidation:
    success: bool
    reason: str = ""


def validate_signup_token(token: str) -> TurnstileValidation:
    if not getattr(settings, "TURNSTILE_ENABLED", False):
        return TurnstileValidation(success=True)
    if not token:
        return TurnstileValidation(success=False, reason="missing_token")

    try:
        response = requests.post(
            SITEVERIFY_URL,
            data={
                "secret": settings.TURNSTILE_SECRET_KEY,
                "response": token,
            },
            timeout=settings.TURNSTILE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return TurnstileValidation(success=False, reason="verification_unavailable")

    if not payload.get("success"):
        return TurnstileValidation(success=False, reason="invalid_token")

    expected_action = getattr(settings, "TURNSTILE_EXPECTED_ACTION", "").strip()
    if expected_action and payload.get("action") != expected_action:
        return TurnstileValidation(success=False, reason="unexpected_action")

    expected_hostnames = {
        hostname.strip()
        for hostname in getattr(
            settings,
            "TURNSTILE_EXPECTED_HOSTNAME",
            "",
        ).split(",")
        if hostname.strip()
    }
    if expected_hostnames and payload.get("hostname") not in expected_hostnames:
        return TurnstileValidation(success=False, reason="unexpected_hostname")

    return TurnstileValidation(success=True)
