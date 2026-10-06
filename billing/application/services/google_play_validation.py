"""Shared Google Play environment and account-binding validation."""

from __future__ import annotations

import hashlib

from billing.models import BillingProduct, GooglePlayAccountToken


class GooglePlayEvidenceError(ValueError):
    pass


def google_play_environment(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in {BillingProduct.Environment.SANDBOX, BillingProduct.Environment.LIVE}:
        raise GooglePlayEvidenceError("Google Play returned an unsupported environment.")
    return normalized


def google_play_account_id(user) -> str:
    return hashlib.sha256(f"myscoope:{user.pk}".encode()).hexdigest()


def get_or_create_google_play_account_token(user) -> GooglePlayAccountToken:
    token, _ = GooglePlayAccountToken.objects.get_or_create(
        user=user,
        defaults={"token": google_play_account_id(user)},
    )
    return token
