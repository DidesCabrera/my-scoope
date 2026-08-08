from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass

import jwt
from django.conf import settings

_DEVICE_TOKEN_PATTERN = re.compile(r"^[0-9a-fA-F]{32,200}$")
_PROVIDER_TOKEN_TTL_SECONDS = 50 * 60
_provider_token_cache: tuple[tuple[str, str, str], str, int] | None = None


@dataclass(frozen=True)
class ApplePushSendResult:
    ok: bool
    expired: bool = False
    failure_code: str = ""


def apple_token_fingerprint(device_token: str) -> str:
    return hashlib.sha256(device_token.encode("ascii")).hexdigest()


def validate_apple_device_token(device_token: str) -> str:
    normalized = (device_token or "").strip().replace(" ", "").replace("<", "").replace(">", "")
    if not _DEVICE_TOKEN_PATTERN.fullmatch(normalized):
        raise ValueError("apns_device_token_invalid")
    return normalized.lower()


def apns_is_configured() -> bool:
    return bool(
        getattr(settings, "MYSCOOPE_APNS_ENABLED", False)
        and getattr(settings, "MYSCOOPE_APNS_KEY_ID", "")
        and getattr(settings, "MYSCOOPE_APNS_TEAM_ID", "")
        and getattr(settings, "MYSCOOPE_APNS_PRIVATE_KEY", "")
        and getattr(settings, "MYSCOOPE_APNS_BUNDLE_ID", "")
    )


def _provider_token(*, now: int | None = None) -> str:
    global _provider_token_cache
    issued_at = int(now if now is not None else time.time())
    private_key = settings.MYSCOOPE_APNS_PRIVATE_KEY.replace("\\n", "\n")
    cache_key = (settings.MYSCOOPE_APNS_KEY_ID, settings.MYSCOOPE_APNS_TEAM_ID, private_key)
    if _provider_token_cache is not None:
        cached_key, cached_token, cached_at = _provider_token_cache
        if cached_key == cache_key and issued_at - cached_at < _PROVIDER_TOKEN_TTL_SECONDS:
            return cached_token
    token = jwt.encode(
        {"iss": settings.MYSCOOPE_APNS_TEAM_ID, "iat": issued_at},
        private_key,
        algorithm="ES256",
        headers={"alg": "ES256", "kid": settings.MYSCOOPE_APNS_KEY_ID},
    )
    _provider_token_cache = (cache_key, token, issued_at)
    return token


def _clear_provider_token_cache() -> None:
    global _provider_token_cache
    _provider_token_cache = None


def _apns_payload(payload: dict) -> dict:
    return {
        "aps": {
            "alert": {
                "title": str(payload.get("title") or "My Scoope")[:80],
                "body": str(payload.get("body") or "Tienes un recordatorio pendiente")[:180],
            },
            "sound": "default",
            "thread-id": "myscoope-program",
        },
        "myscoope": {
            "url": str(payload.get("url") or "/")[:300],
            "tag": str(payload.get("tag") or "")[:120],
        },
    }


def send_apple_push(*, subscription, payload: dict, client=None) -> ApplePushSendResult:
    if not apns_is_configured():
        return ApplePushSendResult(ok=False, failure_code="apns_disabled")

    try:
        token = validate_apple_device_token(subscription.device_token)
        authorization = _provider_token()
    except (ValueError, jwt.PyJWTError):
        return ApplePushSendResult(ok=False, failure_code="apns_credentials_invalid")

    host = (
        "https://api.sandbox.push.apple.com"
        if subscription.environment == "sandbox"
        else "https://api.push.apple.com"
    )
    headers = {
        "authorization": f"bearer {authorization}",
        "apns-topic": settings.MYSCOOPE_APNS_BUNDLE_ID,
        "apns-push-type": "alert",
        "apns-priority": "10",
        "apns-expiration": "0",
    }
    collapse_id = str(payload.get("tag") or "")[:64]
    if collapse_id:
        headers["apns-collapse-id"] = collapse_id

    owns_client = client is None
    if owns_client:
        import httpx

        client = httpx.Client(http2=True, timeout=settings.MYSCOOPE_APNS_TIMEOUT_SECONDS)
    try:
        response = client.post(
            f"{host}/3/device/{token}",
            headers=headers,
            json=_apns_payload(payload),
        )
    except Exception:
        return ApplePushSendResult(ok=False, failure_code="apns_transport_error")
    finally:
        if owns_client:
            client.close()

    if response.status_code == 200:
        return ApplePushSendResult(ok=True)

    try:
        reason = str(response.json().get("reason") or "").strip()
    except (TypeError, ValueError):
        reason = ""
    failure_code = f"apns_{reason}" if reason else f"apns_http_{response.status_code}"
    if reason in {"ExpiredProviderToken", "InvalidProviderToken"}:
        _clear_provider_token_cache()
    expired = response.status_code == 410 or reason in {
        "BadDeviceToken",
        "DeviceTokenNotForTopic",
        "Unregistered",
    }
    return ApplePushSendResult(ok=False, expired=expired, failure_code=failure_code[:80])
