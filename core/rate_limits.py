from __future__ import annotations

from django.conf import settings
from django_ratelimit.decorators import ratelimit


def _rate(name: str, default: str) -> str:
    return str(getattr(settings, name, default) or default).strip()


def login_rate(group, request) -> str:
    return _rate("RATE_LIMIT_LOGIN", "10/m")


def signup_rate(group, request) -> str:
    return _rate("RATE_LIMIT_SIGNUP", "5/m")


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
    return ratelimit(
        key="ip",
        rate=signup_rate,
        method="POST",
        block=True,
        group="accounts.signup",
    )(view_func)


def limit_ai_assistant_turn(view_func):
    return ratelimit(
        key=ai_assistant_turn_key,
        rate=ai_assistant_turn_rate,
        method="POST",
        block=True,
        group="ai_assistant.turn",
    )(view_func)
