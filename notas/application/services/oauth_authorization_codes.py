import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Optional

from django.utils import timezone

from notas.application.services.mcp_user_tokens import (
    create_mcp_user_token,
)
from notas.domain.models import OAuthAuthorizationCode, OAuthClient

OAUTH_AUTHORIZATION_CODE_PREFIX = "oauth_code_"
OAUTH_CODE_CHALLENGE_METHOD_S256 = "S256"
DEFAULT_OAUTH_AUTHORIZATION_CODE_TTL_MINUTES = 5
DEFAULT_OAUTH_ACCESS_TOKEN_TTL_SECONDS = 60 * 60 * 24


@dataclass(frozen=True)
class OAuthAuthorizationCodeCreationResult:
    raw_code: str
    authorization_code: OAuthAuthorizationCode


@dataclass(frozen=True)
class OAuthAuthorizationCodeValidationError:
    code: str
    message: str
    details: dict


@dataclass(frozen=True)
class OAuthAuthorizationCodeValidationResult:
    authorization_code: Optional[OAuthAuthorizationCode] = None
    error: Optional[OAuthAuthorizationCodeValidationError] = None

    @property
    def ok(self) -> bool:
        return self.authorization_code is not None and self.error is None

    @property
    def user(self):
        if self.authorization_code is None:
            return None

        return self.authorization_code.user

    @property
    def client(self):
        if self.authorization_code is None:
            return None

        return self.authorization_code.client


@dataclass(frozen=True)
class OAuthAccessTokenIssueError:
    code: str
    message: str
    details: dict


@dataclass(frozen=True)
class OAuthAccessTokenIssueResult:
    access_token: str = ""
    token_type: str = "Bearer"
    expires_in: int = DEFAULT_OAUTH_ACCESS_TOKEN_TTL_SECONDS
    scope: str = ""
    error: Optional[OAuthAccessTokenIssueError] = None

    @property
    def ok(self) -> bool:
        return bool(self.access_token) and self.error is None

    def as_token_response(self) -> dict:
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "scope": self.scope,
        }


def generate_oauth_authorization_raw_code() -> str:
    return f"{OAUTH_AUTHORIZATION_CODE_PREFIX}{secrets.token_urlsafe(48)}"


def hash_oauth_authorization_code(raw_code: str) -> str:
    return hashlib.sha256(
        raw_code.encode("utf-8"),
    ).hexdigest()


def normalize_oauth_scopes(scopes: Iterable[str] | str | None) -> list[str]:
    if scopes is None:
        return []

    if isinstance(scopes, str):
        scopes = scopes.split()

    normalized = []

    for scope in scopes:
        scope = str(scope).strip()

        if scope and scope not in normalized:
            normalized.append(scope)

    return normalized


def _base64url_sha256(value: str) -> str:
    digest = hashlib.sha256(
        value.encode("utf-8"),
    ).digest()

    return (
        base64.urlsafe_b64encode(digest)
        .decode("ascii")
        .rstrip("=")
    )


def validate_pkce_s256(
    *,
    code_verifier: str,
    code_challenge: str,
) -> bool:
    if not code_verifier or not code_challenge:
        return False

    return secrets.compare_digest(
        _base64url_sha256(code_verifier),
        code_challenge,
    )


def create_oauth_authorization_code(
    *,
    user,
    client: OAuthClient,
    redirect_uri: str,
    scopes: Iterable[str] | str | None,
    code_challenge: str,
    code_challenge_method: str = OAUTH_CODE_CHALLENGE_METHOD_S256,
    expires_at=None,
) -> OAuthAuthorizationCodeCreationResult:
    normalized_scopes = normalize_oauth_scopes(scopes)

    if not client.is_active:
        raise ValueError("oauth_client_inactive")

    if not client.allows_redirect_uri(redirect_uri):
        raise ValueError("oauth_redirect_uri_not_allowed")

    if not client.allows_scopes(normalized_scopes):
        raise ValueError("oauth_scope_not_allowed")

    if code_challenge_method != OAUTH_CODE_CHALLENGE_METHOD_S256:
        raise ValueError("oauth_code_challenge_method_not_supported")

    if not code_challenge:
        raise ValueError("oauth_code_challenge_required")

    raw_code = generate_oauth_authorization_raw_code()

    authorization_code = OAuthAuthorizationCode.objects.create(
        client=client,
        user=user,
        code_hash=hash_oauth_authorization_code(raw_code),
        redirect_uri=redirect_uri,
        scopes=normalized_scopes,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        expires_at=expires_at or (
            timezone.now()
            + timedelta(minutes=DEFAULT_OAUTH_AUTHORIZATION_CODE_TTL_MINUTES)
        ),
    )

    return OAuthAuthorizationCodeCreationResult(
        raw_code=raw_code,
        authorization_code=authorization_code,
    )


def _validation_error(
    *,
    code: str,
    message: str,
    details: Optional[dict] = None,
) -> OAuthAuthorizationCodeValidationResult:
    return OAuthAuthorizationCodeValidationResult(
        error=OAuthAuthorizationCodeValidationError(
            code=code,
            message=message,
            details=details or {},
        )
    )


def validate_oauth_authorization_code(
    *,
    raw_code: str,
    client: OAuthClient,
    redirect_uri: str,
    code_verifier: str,
) -> OAuthAuthorizationCodeValidationResult:
    if not raw_code:
        return _validation_error(
            code="oauth_authorization_code_missing",
            message="Missing OAuth authorization code.",
        )

    code_hash = hash_oauth_authorization_code(raw_code)

    try:
        authorization_code = (
            OAuthAuthorizationCode.objects
            .select_related(
                "client",
                "user",
            )
            .get(code_hash=code_hash)
        )
    except OAuthAuthorizationCode.DoesNotExist:
        return _validation_error(
            code="oauth_authorization_code_invalid",
            message="Invalid OAuth authorization code.",
        )

    if authorization_code.client_id != client.id:
        return _validation_error(
            code="oauth_authorization_code_client_mismatch",
            message="OAuth authorization code was not issued for this client.",
        )

    if authorization_code.redirect_uri != redirect_uri:
        return _validation_error(
            code="oauth_authorization_code_redirect_uri_mismatch",
            message="OAuth authorization code redirect URI does not match.",
        )

    if authorization_code.used_at is not None:
        return _validation_error(
            code="oauth_authorization_code_already_used",
            message="OAuth authorization code has already been used.",
        )

    if authorization_code.expires_at <= timezone.now():
        return _validation_error(
            code="oauth_authorization_code_expired",
            message="OAuth authorization code has expired.",
        )

    if not authorization_code.client.is_active:
        return _validation_error(
            code="oauth_client_inactive",
            message="OAuth client is inactive.",
        )

    if not authorization_code.user.is_active:
        return _validation_error(
            code="oauth_user_inactive",
            message="OAuth authorization code user is inactive.",
            details={
                "user_id": authorization_code.user_id,
            },
        )

    if authorization_code.code_challenge_method != OAUTH_CODE_CHALLENGE_METHOD_S256:
        return _validation_error(
            code="oauth_code_challenge_method_not_supported",
            message="OAuth code challenge method is not supported.",
        )

    if not validate_pkce_s256(
        code_verifier=code_verifier,
        code_challenge=authorization_code.code_challenge,
    ):
        return _validation_error(
            code="oauth_pkce_verification_failed",
            message="OAuth PKCE verification failed.",
        )

    authorization_code.used_at = timezone.now()
    authorization_code.save(
        update_fields=[
            "used_at",
        ]
    )

    return OAuthAuthorizationCodeValidationResult(
        authorization_code=authorization_code,
    )


def _issue_error(
    *,
    code: str,
    message: str,
    details: Optional[dict] = None,
) -> OAuthAccessTokenIssueResult:
    return OAuthAccessTokenIssueResult(
        error=OAuthAccessTokenIssueError(
            code=code,
            message=message,
            details=details or {},
        )
    )


def issue_oauth_access_token_from_authorization_code(
    *,
    raw_code: str,
    client: OAuthClient,
    redirect_uri: str,
    code_verifier: str,
    expires_in: int = DEFAULT_OAUTH_ACCESS_TOKEN_TTL_SECONDS,
) -> OAuthAccessTokenIssueResult:
    validation = validate_oauth_authorization_code(
        raw_code=raw_code,
        client=client,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
    )

    if not validation.ok:
        return _issue_error(
            code=validation.error.code,
            message=validation.error.message,
            details=validation.error.details,
        )

    authorization_code = validation.authorization_code
    scopes = authorization_code.scopes

    expires_at = timezone.now() + timedelta(seconds=expires_in)

    created = create_mcp_user_token(
        user=authorization_code.user,
        name=f"OAuth access token - {authorization_code.client.client_name}",
        scopes=scopes,
        expires_at=expires_at,
    )

    return OAuthAccessTokenIssueResult(
        access_token=created.raw_token,
        token_type="Bearer",
        expires_in=expires_in,
        scope=" ".join(scopes),
    )