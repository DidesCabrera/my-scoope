from __future__ import annotations

import hashlib
import hmac
import time


class InvalidPaddleSignature(ValueError):
    pass


def verify_paddle_signature(
    *,
    raw_body: bytes,
    signature_header: str,
    secret: str,
    tolerance_seconds: int,
    current_time: int | None = None,
) -> None:
    """Verify Paddle-Signature against the untouched request body."""

    if not secret or not signature_header:
        raise InvalidPaddleSignature("Paddle signature configuration is incomplete.")

    timestamp = None
    signatures: list[str] = []
    for component in signature_header.split(";"):
        name, separator, value = component.strip().partition("=")
        if not separator or not value:
            continue
        if name == "ts":
            try:
                timestamp = int(value)
            except ValueError as exc:
                raise InvalidPaddleSignature("Paddle signature timestamp is invalid.") from exc
        elif name == "h1":
            signatures.append(value)

    if timestamp is None or not signatures:
        raise InvalidPaddleSignature("Paddle signature fields are missing.")
    now = int(time.time()) if current_time is None else int(current_time)
    if tolerance_seconds < 0 or abs(now - timestamp) > tolerance_seconds:
        raise InvalidPaddleSignature("Paddle signature timestamp is outside tolerance.")

    signed_payload = str(timestamp).encode("ascii") + b":" + raw_body
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise InvalidPaddleSignature("Paddle signature does not match.")
