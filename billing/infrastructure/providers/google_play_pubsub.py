"""Authenticated Cloud Pub/Sub envelope handling for Google Play RTDN."""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from typing import Any

import jwt


class GooglePubSubConfigurationError(RuntimeError):
    pass


class InvalidGooglePubSubPush(ValueError):
    pass


@dataclass(frozen=True)
class GooglePlayNotification:
    message_id: str
    package_name: str
    event_time_millis: str
    kind: str
    notification_type: str
    purchase_token: str = ""
    product_id: str = ""
    published_at: str = ""


_JWK_CLIENT = jwt.PyJWKClient("https://www.googleapis.com/oauth2/v3/certs", cache_keys=True)


def verify_google_pubsub_authorization(
    authorization_header: str,
    *,
    audience: str,
    service_account_email: str,
    jwk_client=None,
) -> dict[str, Any]:
    if not audience or not service_account_email:
        raise GooglePubSubConfigurationError("Google Pub/Sub push authentication is incomplete.")
    scheme, separator, encoded = str(authorization_header or "").partition(" ")
    if scheme.lower() != "bearer" or not separator or not encoded.strip():
        raise InvalidGooglePubSubPush("Google Pub/Sub authorization is missing.")
    try:
        key = (jwk_client or _JWK_CLIENT).get_signing_key_from_jwt(encoded.strip()).key
        claims = jwt.decode(
            encoded.strip(),
            key,
            algorithms=["RS256"],
            audience=audience,
            issuer=("accounts.google.com", "https://accounts.google.com"),
            options={"require": ["aud", "email", "email_verified", "exp", "iat", "iss"]},
        )
    except jwt.PyJWKClientConnectionError as exc:
        raise GooglePubSubConfigurationError("Google Pub/Sub signing keys are unavailable.") from exc
    except jwt.PyJWTError as exc:
        raise InvalidGooglePubSubPush("Google Pub/Sub authorization is invalid.") from exc
    if str(claims.get("email") or "").lower() != service_account_email.lower():
        raise InvalidGooglePubSubPush("Google Pub/Sub service account does not match.")
    if claims.get("email_verified") is not True:
        raise InvalidGooglePubSubPush("Google Pub/Sub service account is not verified.")
    return claims


def decode_google_play_notification(envelope: object) -> GooglePlayNotification:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("message"), dict):
        raise InvalidGooglePubSubPush("Google Pub/Sub envelope is invalid.")
    message = envelope["message"]
    message_id = str(message.get("messageId") or "").strip()
    encoded_data = str(message.get("data") or "").strip()
    if not message_id or not encoded_data:
        raise InvalidGooglePubSubPush("Google Pub/Sub message identity is incomplete.")
    try:
        decoded = base64.b64decode(encoded_data, validate=True)
        payload = json.loads(decoded.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, TypeError, ValueError) as exc:
        raise InvalidGooglePubSubPush("Google Play notification data is invalid.") from exc
    if not isinstance(payload, dict):
        raise InvalidGooglePubSubPush("Google Play notification payload is invalid.")

    variants = [
        key
        for key in (
            "subscriptionNotification",
            "oneTimeProductNotification",
            "voidedPurchaseNotification",
            "testNotification",
        )
        if key in payload
    ]
    if len(variants) != 1 or not isinstance(payload[variants[0]], dict):
        raise InvalidGooglePubSubPush("Google Play notification type is invalid.")
    variant = variants[0]
    detail = payload[variant]
    kind = {
        "subscriptionNotification": "subscription",
        "oneTimeProductNotification": "one_time_product",
        "voidedPurchaseNotification": "voided_purchase",
        "testNotification": "test",
    }[variant]
    purchase_token = str(detail.get("purchaseToken") or "").strip()
    product_id = str(detail.get("subscriptionId") or detail.get("sku") or "").strip()
    if kind != "test" and not purchase_token:
        raise InvalidGooglePubSubPush("Google Play purchase token is missing.")
    return GooglePlayNotification(
        message_id=message_id,
        package_name=str(payload.get("packageName") or "").strip(),
        event_time_millis=str(payload.get("eventTimeMillis") or "").strip(),
        kind=kind,
        notification_type=str(detail.get("notificationType") or "test").strip(),
        purchase_token=purchase_token,
        product_id=product_id,
        published_at=str(message.get("publishTime") or "").strip(),
    )
