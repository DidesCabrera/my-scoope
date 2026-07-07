from __future__ import annotations

from collections.abc import Mapping
from typing import Any


FILTERED = "[Filtered]"
SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "csrf",
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "openai",
    "prompt",
    "messages",
    "input",
    "output",
    "payload",
    "tool_payload",
    "tool_result",
    "tool_results",
    "request_body",
    "body",
)
SENSITIVE_REQUEST_KEYS = {"headers", "data", "json", "body", "cookies", "env"}


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def sanitize_for_observability(value: Any, *, depth: int = 0, parent_key: Any = "") -> Any:
    if depth > 8:
        return FILTERED
    if _is_sensitive_key(parent_key):
        return FILTERED
    if isinstance(value, Mapping):
        return {
            key: sanitize_for_observability(item, depth=depth + 1, parent_key=key)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_for_observability(item, depth=depth + 1) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_for_observability(item, depth=depth + 1) for item in value)
    return value


def sanitize_sentry_event(event: dict[str, Any], hint: Any | None = None) -> dict[str, Any]:
    sanitized = sanitize_for_observability(event)
    request = sanitized.get("request")
    if isinstance(request, dict):
        for key in SENSITIVE_REQUEST_KEYS:
            if key in request:
                request[key] = FILTERED
    return sanitized


def configure_sentry(
    *,
    dsn: str,
    environment: str,
    release: str,
    traces_sample_rate: float,
    profiles_sample_rate: float,
) -> bool:
    if not dsn:
        return False

    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=dsn,
        integrations=[DjangoIntegration()],
        environment=environment or None,
        release=release or None,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        send_default_pii=False,
        before_send=sanitize_sentry_event,
    )
    return True
