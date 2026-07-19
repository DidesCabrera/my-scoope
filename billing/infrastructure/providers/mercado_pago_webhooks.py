"""Mercado Pago webhook authentication at the infrastructure boundary."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass


class InvalidMercadoPagoSignature(ValueError):
    pass


@dataclass(frozen=True)
class MercadoPagoSignature:
    timestamp: int
    digest: str


def verify_mercado_pago_signature(
    *,
    signature_header: str,
    request_id: str,
    data_id: str,
    secret: str,
    tolerance_seconds: int = 300,
    now_seconds: float | None = None,
) -> MercadoPagoSignature:
    if not secret:
        raise InvalidMercadoPagoSignature("Webhook secret is not configured.")
    parts = _parse_signature_header(signature_header)
    timestamp_raw = parts.get("ts", "")
    received_digest = parts.get("v1", "")
    if not timestamp_raw or not received_digest or not request_id or not data_id:
        raise InvalidMercadoPagoSignature("Webhook signature fields are incomplete.")
    try:
        timestamp_value = int(timestamp_raw)
    except ValueError as exc:
        raise InvalidMercadoPagoSignature("Webhook timestamp is invalid.") from exc

    event_seconds = timestamp_value / 1000 if timestamp_value >= 1_000_000_000_000 else timestamp_value
    current_seconds = time.time() if now_seconds is None else now_seconds
    if tolerance_seconds >= 0 and abs(current_seconds - event_seconds) > tolerance_seconds:
        raise InvalidMercadoPagoSignature("Webhook timestamp is outside the accepted tolerance.")

    normalized_data_id = data_id.lower() if data_id.isalnum() else data_id
    manifest = f"id:{normalized_data_id};request-id:{request_id};ts:{timestamp_raw};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_digest):
        raise InvalidMercadoPagoSignature("Webhook signature does not match.")
    return MercadoPagoSignature(timestamp=timestamp_value, digest=received_digest)


def _parse_signature_header(value: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for item in (value or "").split(","):
        key, separator, raw_value = item.partition("=")
        if separator:
            parts[key.strip()] = raw_value.strip()
    return parts
