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


def is_nutrition_label_scan_rate_limited(request) -> bool:
    return bool(is_ratelimited(
        request=request,
        key="user",
        rate=lambda group, req: _rate("RATE_LIMIT_NUTRITION_LABEL_SCAN_USER", "10/h"),
        method="POST",
        group="nutrition_label.scan",
        increment=True,
    ))


def sharing_actor_key(group, request) -> str:
    user = getattr(request, "user", None)
    auth = getattr(request, "auth", None)
    if (user is None or not user.is_authenticated) and getattr(auth, "user", None):
        user = auth.user
    if user is not None and user.is_authenticated:
        return f"user:{user.pk}"
    return f"ip:{request.META.get('REMOTE_ADDR', '')}"


def limit_sharing_preview(view_func):
    return ratelimit(
        key="ip",
        rate=lambda group, request: _rate("RATE_LIMIT_SHARING_PREVIEW_IP", "120/m"),
        method="GET",
        block=True,
        group="sharing.preview",
    )(view_func)


def limit_sharing_claim(view_func):
    return ratelimit(
        key=sharing_actor_key,
        rate=lambda group, request: _rate("RATE_LIMIT_SHARING_CLAIM", "20/h"),
        method="POST",
        block=True,
        group="sharing.claim",
    )(view_func)


def limit_sharing_create(view_func):
    return ratelimit(
        key="user",
        rate=lambda group, request: _rate("RATE_LIMIT_SHARING_CREATE_USER", "30/h"),
        method="POST",
        block=True,
        group="sharing.create",
    )(view_func)


def is_sharing_create_rate_limited(request) -> bool:
    return bool(is_ratelimited(
        request=request,
        key=lambda group, req: f"user:{req.auth.user.pk}",
        rate=lambda group, req: _rate("RATE_LIMIT_SHARING_CREATE_USER", "30/h"),
        method="POST",
        group="sharing.create",
        increment=True,
    ))


def is_sharing_claim_rate_limited(request) -> bool:
    return bool(is_ratelimited(
        request=request,
        key=sharing_actor_key,
        rate=lambda group, req: _rate("RATE_LIMIT_SHARING_CLAIM", "20/h"),
        method="POST",
        group="sharing.claim",
        increment=True,
    ))


def is_sharing_preview_rate_limited(request) -> bool:
    return bool(is_ratelimited(
        request=request,
        key="ip",
        rate=lambda group, req: _rate("RATE_LIMIT_SHARING_PREVIEW_IP", "120/m"),
        method="GET",
        group="sharing.preview",
        increment=True,
    ))
