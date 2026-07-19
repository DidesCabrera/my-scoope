from __future__ import annotations

import hashlib
import ipaddress
import json
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

from django.conf import settings


@dataclass(frozen=True)
class WebPushSendResult:
    ok: bool
    expired: bool = False
    failure_code: str = ""


def endpoint_fingerprint(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


def _is_forbidden_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )


def validate_push_endpoint(endpoint: str, *, resolve_dns: bool = False) -> str:
    clean_endpoint = (endpoint or "").strip()
    if not clean_endpoint or len(clean_endpoint) > 2048:
        raise ValueError("push_endpoint_invalid")

    parsed = urlparse(clean_endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("push_endpoint_invalid")
    if parsed.port not in (None, 443):
        raise ValueError("push_endpoint_invalid")

    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("push_endpoint_forbidden")

    try:
        if _is_forbidden_ip(host):
            raise ValueError("push_endpoint_forbidden")
    except ValueError as exc:
        if str(exc) == "push_endpoint_forbidden":
            raise

    if resolve_dns:
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        except OSError as exc:
            raise ValueError("push_endpoint_unresolvable") from exc
        if not addresses or any(_is_forbidden_ip(address) for address in addresses):
            raise ValueError("push_endpoint_forbidden")

    return clean_endpoint


def build_daily_plan_push_payload(*, calendarized_day_id: int) -> dict:
    return {
        "title": "MyScoope",
        "body": "Tu plan diario está listo",
        "url": f"/app/calendarization/days/{calendarized_day_id}/",
        "tag": f"myscoope-calendarized-day-{calendarized_day_id}",
    }


def send_web_push(*, subscription, payload: dict) -> WebPushSendResult:
    if not getattr(settings, "MYSCOOPE_WEB_PUSH_ENABLED", False):
        return WebPushSendResult(ok=False, failure_code="web_push_disabled")

    try:
        validate_push_endpoint(subscription.endpoint, resolve_dns=True)
    except (OSError, ValueError):
        return WebPushSendResult(ok=False, failure_code="push_endpoint_rejected")

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        return WebPushSendResult(ok=False, failure_code="pywebpush_unavailable")

    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh_key,
                    "auth": subscription.auth_key,
                },
            },
            data=json.dumps(payload, separators=(",", ":")),
            vapid_private_key=settings.MYSCOOPE_VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.MYSCOOPE_VAPID_SUBJECT},
            timeout=10,
            ttl=7200,
        )
    except WebPushException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in {404, 410}:
            return WebPushSendResult(ok=False, expired=True, failure_code=f"http_{status_code}")
        return WebPushSendResult(ok=False, failure_code=f"http_{status_code}" if status_code else "web_push_error")
    except (OSError, ValueError):
        return WebPushSendResult(ok=False, failure_code="web_push_transport_error")

    return WebPushSendResult(ok=True)
