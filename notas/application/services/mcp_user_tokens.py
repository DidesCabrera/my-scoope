import hashlib
import secrets
from dataclasses import dataclass
from typing import Iterable, Optional

from django.conf import settings
from django.utils import timezone

from accounts.services.entitlements import has_mcp_access
from notas.domain.models import MCPUserToken

MCP_USER_TOKEN_PREFIX = "mcp_user_"

MCP_SCOPE_READ = "myscoope:read"
MCP_SCOPE_PROPOSALS_CREATE = "myscoope:proposals:create"

DEFAULT_MCP_USER_TOKEN_SCOPES = [
    MCP_SCOPE_READ,
]
MCP_COMMERCIAL_SCOPES = frozenset({MCP_SCOPE_READ, MCP_SCOPE_PROPOSALS_CREATE})


def mcp_pro_access_required(user, scopes: Iterable[str]) -> bool:
    """Keep mobile OAuth scopes independent from the optional MCP PRO gate."""
    return (
        getattr(settings, "MCP_PRO_ENTITLEMENT_ENFORCED", False)
        and bool(MCP_COMMERCIAL_SCOPES.intersection(scopes))
        and not has_mcp_access(user)
    )


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
    device_session=None,
    resource: str = "",
) -> MCPUserTokenCreationResult:
    resolved_scopes = list(scopes or DEFAULT_MCP_USER_TOKEN_SCOPES)
    if mcp_pro_access_required(user, resolved_scopes):
        raise ValueError("mcp_pro_required")

    if getattr(settings, "MCP_PRO_ENTITLEMENT_ENFORCED", False) and MCP_COMMERCIAL_SCOPES.intersection(resolved_scopes):
        expected_resource = getattr(settings, "MCP_RESOURCE_URL", "")
        if not expected_resource:
            raise ValueError("mcp_resource_not_configured")
        if resource != expected_resource:
            raise ValueError("mcp_resource_not_allowed")
        if expires_at is None or expires_at <= timezone.now():
            raise ValueError("mcp_token_expiry_required")

    raw_token = generate_mcp_user_raw_token()

    token = MCPUserToken.objects.create(
        user=user,
        name=name,
        token_hash=hash_mcp_user_token(raw_token),
        scopes=resolved_scopes,
        resource=resource,
        expires_at=expires_at,
        device_session=device_session,
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
    required_resource: str | None = None,
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
            .select_related("user", "device_session")
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

    if mcp_pro_access_required(token.user, token.scopes):
        return MCPUserTokenValidationResult(
            error=MCPUserTokenValidationError(
                code="mcp_pro_required",
                message="An active PRO subscription is required for MCP access.",
                details={},
            )
        )

    if required_resource is None and (
        getattr(settings, "MCP_PRO_ENTITLEMENT_ENFORCED", False)
        and MCP_COMMERCIAL_SCOPES.intersection(token.scopes)
    ):
        required_resource = getattr(settings, "MCP_RESOURCE_URL", "")

    if required_resource is not None and (
        not required_resource or token.resource != required_resource
    ):
        return MCPUserTokenValidationResult(
            error=MCPUserTokenValidationError(
                code="mcp_user_token_wrong_resource",
                message="MCP user token is not valid for this resource.",
                details={},
            )
        )

    if required_resource is not None and token.expires_at is None:
        return MCPUserTokenValidationResult(
            error=MCPUserTokenValidationError(
                code="mcp_user_token_expiry_required",
                message="An expiring token is required for MCP access.",
                details={},
            )
        )

    if token.device_session_id and (
        not token.device_session.is_active
        or token.device_session.revoked_at is not None
    ):
        return MCPUserTokenValidationResult(
            error=MCPUserTokenValidationError(
                code="mcp_user_token_device_session_revoked",
                message="The device session for this token has been revoked.",
                details={
                    "device_session_id": str(token.device_session.public_id),
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
