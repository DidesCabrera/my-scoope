import hashlib
import secrets
from dataclasses import dataclass
from typing import Iterable, Optional

from django.utils import timezone

from notas.domain.models import MCPUserToken

MCP_USER_TOKEN_PREFIX = "mcp_user_"

MCP_SCOPE_READ = "myscoope:read"
MCP_SCOPE_PROPOSALS_CREATE = "myscoope:proposals:create"

DEFAULT_MCP_USER_TOKEN_SCOPES = [
    MCP_SCOPE_READ,
    MCP_SCOPE_PROPOSALS_CREATE,
]


@dataclass(frozen=True)
class MCPUserTokenCreationResult:
    raw_token: str
    token: MCPUserToken


@dataclass(frozen=True)
class MCPUserTokenValidationError:
    code: str
    message: str
    details: dict


@dataclass(frozen=True)
class MCPUserTokenValidationResult:
    token: Optional[MCPUserToken] = None
    error: Optional[MCPUserTokenValidationError] = None

    @property
    def ok(self) -> bool:
        return self.token is not None and self.error is None

    @property
    def user(self):
        if self.token is None:
            return None

        return self.token.user


def generate_mcp_user_raw_token() -> str:
    return f"{MCP_USER_TOKEN_PREFIX}{secrets.token_urlsafe(48)}"


def hash_mcp_user_token(raw_token: str) -> str:
    return hashlib.sha256(
        raw_token.encode("utf-8"),
    ).hexdigest()


def create_mcp_user_token(
    *,
    user,
    name: str,
    scopes: Optional[Iterable[str]] = None,
    expires_at=None,
) -> MCPUserTokenCreationResult:
    raw_token = generate_mcp_user_raw_token()

    token = MCPUserToken.objects.create(
        user=user,
        name=name,
        token_hash=hash_mcp_user_token(raw_token),
        scopes=list(scopes or DEFAULT_MCP_USER_TOKEN_SCOPES),
        expires_at=expires_at,
    )

    return MCPUserTokenCreationResult(
        raw_token=raw_token,
        token=token,
    )


def _missing_required_scopes(
    token: MCPUserToken,
    required_scopes: Iterable[str],
) -> list[str]:
    return [
        scope
        for scope in required_scopes
        if not token.has_scope(scope)
    ]


def validate_mcp_user_token(
    raw_token: str,
    *,
    required_scopes: Optional[Iterable[str]] = None,
) -> MCPUserTokenValidationResult:
    if not raw_token:
        return MCPUserTokenValidationResult(
            error=MCPUserTokenValidationError(
                code="mcp_user_token_missing",
                message="Missing MCP user token.",
                details={},
            )
        )

    token_hash = hash_mcp_user_token(raw_token)

    try:
        token = (
            MCPUserToken.objects
            .select_related("user")
            .get(token_hash=token_hash)
        )
    except MCPUserToken.DoesNotExist:
        return MCPUserTokenValidationResult(
            error=MCPUserTokenValidationError(
                code="mcp_user_token_invalid",
                message="Invalid MCP user token.",
                details={},
            )
        )

    if token.revoked_at is not None:
        return MCPUserTokenValidationResult(
            error=MCPUserTokenValidationError(
                code="mcp_user_token_revoked",
                message="MCP user token has been revoked.",
                details={},
            )
        )

    if not token.is_active:
        return MCPUserTokenValidationResult(
            error=MCPUserTokenValidationError(
                code="mcp_user_token_inactive",
                message="MCP user token is inactive.",
                details={},
            )
        )

    if token.expires_at is not None and token.expires_at <= timezone.now():
        return MCPUserTokenValidationResult(
            error=MCPUserTokenValidationError(
                code="mcp_user_token_expired",
                message="MCP user token has expired.",
                details={},
            )
        )

    if not token.user.is_active:
        return MCPUserTokenValidationResult(
            error=MCPUserTokenValidationError(
                code="mcp_user_token_user_inactive",
                message="MCP user token owner is inactive.",
                details={
                    "user_id": token.user_id,
                },
            )
        )

    missing_scopes = _missing_required_scopes(
        token,
        required_scopes or [],
    )

    if missing_scopes:
        return MCPUserTokenValidationResult(
            error=MCPUserTokenValidationError(
                code="mcp_user_token_missing_scope",
                message="MCP user token does not include the required scope.",
                details={
                    "missing_scopes": missing_scopes,
                },
            )
        )

    token.last_used_at = timezone.now()
    token.save(
        update_fields=[
            "last_used_at",
        ]
    )

    return MCPUserTokenValidationResult(
        token=token,
    )


def revoke_mcp_user_token(
    token: MCPUserToken,
) -> MCPUserToken:
    token.revoked_at = timezone.now()
    token.is_active = False
    token.save(
        update_fields=[
            "revoked_at",
            "is_active",
        ]
    )

    return token