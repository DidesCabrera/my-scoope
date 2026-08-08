from __future__ import annotations

from django.conf import settings
from django_ratelimit.core import is_ratelimited
from django_ratelimit.decorators import ratelimit


def _rate(name: str, default: str) -> str:
    return str(getattr(settings, name, default) or default).strip()


def login_rate(group, request) -> str:
    return _rate("RATE_LIMIT_LOGIN", "10/m")


def signup_rate(group, request) -> str:
    return _rate("RATE_LIMIT_SIGNUP", "3/10m")


def signup_ip_daily_rate(group, request) -> str:
    return _rate("RATE_LIMIT_SIGNUP_IP_DAILY", "10/d")


def signup_email_daily_rate(group, request) -> str:
    return _rate("RATE_LIMIT_SIGNUP_EMAIL_DAILY", "3/d")


def signup_email_key(group, request) -> str:
    return str(request.POST.get("email", "")).strip().lower()


def ai_assistant_turn_rate(group, request) -> str:
    if getattr(request, "user", None) and request.user.is_authenticated:
        return _rate("RATE_LIMIT_AI_ASSISTANT_TURN_USER", "20/h")
    return _rate("RATE_LIMIT_AI_ASSISTANT_TURN_IP", "5/h")


def ai_assistant_turn_key(group, request) -> str:
    if getattr(request, "user", None) and request.user.is_authenticated:
        return "user"
    return "ip"


def limit_login(view_func):
    return ratelimit(
        key="ip",
        rate=login_rate,
        method="POST",
        block=True,
        group="accounts.login",
    )(view_func)


def limit_signup(view_func):
    email_limited = ratelimit(
        key=signup_email_key,
        rate=signup_email_daily_rate,
        method="POST",
        block=True,
        group="accounts.signup.email.daily",
    )(view_func)
    daily_limited = ratelimit(
        key="ip",
        rate=signup_ip_daily_rate,
        method="POST",
        block=True,
        group="accounts.signup.ip.daily",
    )(email_limited)
    return ratelimit(
        key="ip",
        rate=signup_rate,
        method="POST",
        block=True,
        group="accounts.signup.ip.burst",
    )(daily_limited)


def limit_ai_assistant_turn(view_func):
    return ratelimit(
        key=ai_assistant_turn_key,
        rate=ai_assistant_turn_rate,
        method="POST",
        block=True,
        group="ai_assistant.turn",
    )(view_func)


def is_ai_assistant_turn_rate_limited(request) -> bool:
    """Consume the shared AI limit while allowing JSON interfaces to own the response."""

    return bool(is_ratelimited(
        request=request,
        key=ai_assistant_turn_key,
        rate=ai_assistant_turn_rate,
        method="POST",
        group="ai_assistant.turn",
        increment=True,
    ))
