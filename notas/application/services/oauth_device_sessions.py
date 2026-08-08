from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_authorization_codes import (
    OAuthAccessTokenIssueError,
    validate_oauth_authorization_code,
)
from notas.domain.models import OAuthClient, OAuthDeviceSession, OAuthRefreshToken

MOBILE_SCOPE_READ = "mobile:read"
MOBILE_SCOPE_WRITE = "mobile:write"
MOBILE_SCOPE_ACCOUNT = "mobile:account"
MOBILE_SCOPES = (MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE, MOBILE_SCOPE_ACCOUNT)

OAUTH_REFRESH_TOKEN_PREFIX = "oauth_refresh_"
MOBILE_ACCESS_TOKEN_TTL_SECONDS = 15 * 60
MOBILE_REFRESH_TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60


@dataclass(frozen=True)
class OAuthMobileTokenIssueResult:
    access_token: str = ""
    refresh_token: str = ""
    token_type: str = "Bearer"
    expires_in: int = MOBILE_ACCESS_TOKEN_TTL_SECONDS
    refresh_expires_in: int = MOBILE_REFRESH_TOKEN_TTL_SECONDS
    scope: str = ""
    device_session_id: str = ""
    error: OAuthAccessTokenIssueError | None = None

    @property
    def ok(self) -> bool:
        return bool(self.access_token and self.refresh_token) and self.error is None

    def as_token_response(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "refresh_expires_in": self.refresh_expires_in,
            "scope": self.scope,
            "device_session_id": self.device_session_id,
        }


def _issue_error(code: str, message: str, *, details: dict | None = None) -> OAuthMobileTokenIssueResult:
    return OAuthMobileTokenIssueResult(
        error=OAuthAccessTokenIssueError(
            code=code,
            message=message,
            details=details or {},
        )
    )


def hash_oauth_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def hash_oauth_device_id(*, client_id: str, device_id: str) -> str:
    normalized = f"{client_id}:{device_id.strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _generate_refresh_token() -> str:
    return f"{OAUTH_REFRESH_TOKEN_PREFIX}{secrets.token_urlsafe(64)}"


def _validate_device_input(*, device_id: str, platform: str) -> str | None:
    device_id = (device_id or "").strip()
    if len(device_id) < 16 or len(device_id) > 255:
        return "oauth_device_id_invalid"
    if platform not in dict(OAuthDeviceSession.PLATFORM_CHOICES):
        return "oauth_device_platform_invalid"
    return None


def _revoke_session(session: OAuthDeviceSession, *, now) -> None:
    session.is_active = False
    session.revoked_at = now
    session.save(update_fields=["is_active", "revoked_at", "updated_at"])
    session.access_tokens.filter(is_active=True).update(is_active=False, revoked_at=now)
    session.refresh_tokens.filter(revoked_at__isnull=True).update(revoked_at=now)


def _issue_pair(
    *,
    session: OAuthDeviceSession,
    scopes: list[str],
    family_id: uuid.UUID | None = None,
    now,
) -> tuple[OAuthMobileTokenIssueResult, OAuthRefreshToken]:
    access_expiry = now + timedelta(seconds=MOBILE_ACCESS_TOKEN_TTL_SECONDS)
    refresh_expiry = now + timedelta(seconds=MOBILE_REFRESH_TOKEN_TTL_SECONDS)
    access = create_mcp_user_token(
        user=session.user,
        name=f"Mobile access token · {session.device_name or session.platform}",
        scopes=scopes,
        expires_at=access_expiry,
        device_session=session,
    )
    raw_refresh_token = _generate_refresh_token()
    refresh = OAuthRefreshToken.objects.create(
        session=session,
        family_id=family_id or uuid.uuid4(),
        token_hash=hash_oauth_refresh_token(raw_refresh_token),
        scopes=scopes,
        expires_at=refresh_expiry,
    )
    result = OAuthMobileTokenIssueResult(
        access_token=access.raw_token,
        refresh_token=raw_refresh_token,
        scope=" ".join(scopes),
        device_session_id=str(session.public_id),
    )
    return result, refresh


@transaction.atomic
def issue_mobile_tokens_from_authorization_code(
    *,
    raw_code: str,
    client: OAuthClient,
    redirect_uri: str,
    code_verifier: str,
    device_id: str,
    device_name: str,
    platform: str,
) -> OAuthMobileTokenIssueResult:
    device_error = _validate_device_input(device_id=device_id, platform=platform)
    if device_error:
        return _issue_error(device_error, "Mobile device identification is invalid.")

    validation = validate_oauth_authorization_code(
        raw_code=raw_code,
        client=client,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
    )
    if not validation.ok:
        return _issue_error(
            validation.error.code,
            validation.error.message,
            details=validation.error.details,
        )

    scopes = list(validation.authorization_code.scopes)
    if not any(scope in MOBILE_SCOPES for scope in scopes):
        return _issue_error("oauth_mobile_scope_required", "A mobile OAuth scope is required.")

    now = timezone.now()
    device_id_hash = hash_oauth_device_id(client_id=client.client_id, device_id=device_id)
    session = (
        OAuthDeviceSession.objects.select_for_update()
        .filter(client=client, user=validation.user, device_id_hash=device_id_hash)
        .first()
    )
    if session is None:
        session = OAuthDeviceSession.objects.create(
            client=client,
            user=validation.user,
            device_id_hash=device_id_hash,
            device_name=(device_name or "")[:120],
            platform=platform,
            last_used_at=now,
        )
    else:
        _revoke_session(session, now=now)
        session.device_name = (device_name or "")[:120]
        session.platform = platform
        session.is_active = True
        session.revoked_at = None
        session.last_used_at = now
        session.save(
            update_fields=["device_name", "platform", "is_active", "revoked_at", "last_used_at", "updated_at"]
        )

    result, _refresh = _issue_pair(session=session, scopes=scopes, now=now)
    return result


@transaction.atomic
def rotate_mobile_refresh_token(
    *,
    raw_refresh_token: str,
    client: OAuthClient,
) -> OAuthMobileTokenIssueResult:
    now = timezone.now()
    token_hash = hash_oauth_refresh_token(raw_refresh_token or "")
    try:
        refresh = (
            OAuthRefreshToken.objects.select_for_update()
            .select_related("session__user", "session__client")
            .get(token_hash=token_hash)
        )
    except OAuthRefreshToken.DoesNotExist:
        return _issue_error("oauth_refresh_token_invalid", "Refresh token is invalid.")

    session = refresh.session
    if session.client_id != client.id:
        return _issue_error("oauth_refresh_token_client_mismatch", "Refresh token was issued for another client.")
    if refresh.rotated_at is not None:
        _revoke_session(session, now=now)
        return _issue_error(
            "oauth_refresh_token_reused",
            "Refresh token reuse was detected and the device session was revoked.",
        )
    if refresh.revoked_at is not None or not session.is_active or session.revoked_at is not None:
        return _issue_error("oauth_refresh_token_revoked", "Refresh token has been revoked.")
    if refresh.expires_at <= now:
        refresh.revoked_at = now
        refresh.save(update_fields=["revoked_at"])
        return _issue_error("oauth_refresh_token_expired", "Refresh token has expired.")
    if not session.user.is_active:
        _revoke_session(session, now=now)
        return _issue_error("oauth_user_inactive", "Refresh token owner is inactive.")
    scopes = list(refresh.scopes)
    if not client.allows_scopes(scopes):
        _revoke_session(session, now=now)
        return _issue_error("oauth_scope_not_allowed", "Refresh token scopes are no longer allowed.")

    result, replacement = _issue_pair(
        session=session,
        scopes=scopes,
        family_id=refresh.family_id,
        now=now,
    )
    refresh.rotated_at = now
    refresh.replaced_by = replacement
    refresh.save(update_fields=["rotated_at", "replaced_by"])
    session.last_used_at = now
    session.save(update_fields=["last_used_at", "updated_at"])
    return result


@transaction.atomic
def revoke_oauth_device_session(*, user, public_id: str) -> bool:
    try:
        session = OAuthDeviceSession.objects.select_for_update().get(public_id=public_id, user=user)
    except (OAuthDeviceSession.DoesNotExist, ValueError):
        return False
    if not session.is_active:
        return True
    _revoke_session(session, now=timezone.now())
    return True
