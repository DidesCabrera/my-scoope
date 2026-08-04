import os
from dataclasses import dataclass
from typing import Iterable, Optional

from django.contrib.auth import get_user_model

from notas.application.services.mcp_user_tokens import (
    MCP_USER_TOKEN_PREFIX,
    MCPUserTokenValidationError,
    validate_mcp_user_token,
)

INTERNAL_API_AUTH_HEADER_PREFIX = "Bearer "


@dataclass(frozen=True)
class InternalAPIAuthError:
    code: str
    message: str
    details: dict
    status_code: int = 401


@dataclass(frozen=True)
class InternalAPIAuthResult:
    user: Optional[object] = None
    error: Optional[InternalAPIAuthError] = None
    auth_source: str = ""

    @property
    def ok(self) -> bool:
        return self.user is not None and self.error is None


def get_authorization_header(request) -> str:
    return request.META.get("HTTP_AUTHORIZATION", "")


def extract_bearer_token(request) -> str:
    authorization = get_authorization_header(request)

    if not authorization:
        return ""

    if not authorization.startswith(INTERNAL_API_AUTH_HEADER_PREFIX):
        return ""

    return authorization[len(INTERNAL_API_AUTH_HEADER_PREFIX):].strip()


def get_configured_internal_api_token() -> str:
    return os.getenv("MYSCOOPE_INTERNAL_API_TOKEN", "").strip()


def get_configured_internal_api_username() -> str:
    return os.getenv("MYSCOOPE_INTERNAL_API_USERNAME", "").strip()


def _mcp_user_token_error_to_internal_api_error(
    error: MCPUserTokenValidationError,
) -> InternalAPIAuthError:
    status_code = 401

    if error.code == "mcp_user_token_missing_scope":
        status_code = 403

    return InternalAPIAuthError(
        code=error.code,
        message=error.message,
        details=error.details,
        status_code=status_code,
    )


def _resolve_mcp_user_token_user(
    token: str,
    *,
    required_scopes: Optional[Iterable[str]] = None,
) -> InternalAPIAuthResult:
    result = validate_mcp_user_token(
        token,
        required_scopes=required_scopes,
    )

    if not result.ok:
        return InternalAPIAuthResult(
            error=_mcp_user_token_error_to_internal_api_error(
                result.error,
            ),
            auth_source="mcp_user_token",
        )

    return InternalAPIAuthResult(
        user=result.user,
        auth_source="mcp_user_token",
    )


def _resolve_legacy_internal_api_user(
    token: str,
) -> InternalAPIAuthResult:
    expected_token = get_configured_internal_api_token()

    if not expected_token:
        return InternalAPIAuthResult(
            error=InternalAPIAuthError(
                code="internal_api_auth_not_configured",
                message="Internal API authentication token is not configured.",
                details={},
            ),
            auth_source="internal_api",
        )

    if token != expected_token:
        return InternalAPIAuthResult(
            error=InternalAPIAuthError(
                code="internal_api_auth_invalid",
                message="Invalid internal API bearer token.",
                details={},
            ),
            auth_source="internal_api",
        )

    username = get_configured_internal_api_username()

    if not username:
        return InternalAPIAuthResult(
            error=InternalAPIAuthError(
                code="internal_api_auth_user_not_configured",
                message="Internal API username is not configured.",
                details={},
            ),
            auth_source="internal_api",
        )

    User = get_user_model()

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return InternalAPIAuthResult(
            error=InternalAPIAuthError(
                code="internal_api_auth_user_not_found",
                message="Configured internal API user was not found.",
                details={
                    "username": username,
                },
            ),
            auth_source="internal_api",
        )

    if not user.is_active:
        return InternalAPIAuthResult(
            error=InternalAPIAuthError(
                code="internal_api_auth_user_inactive",
                message="Configured internal API user is inactive.",
                details={
                    "username": username,
                },
            ),
            auth_source="internal_api",
        )

    return InternalAPIAuthResult(
        user=user,
        auth_source="internal_api",
    )


def resolve_internal_api_user(
    request,
    *,
    required_scopes: Optional[Iterable[str]] = None,
) -> InternalAPIAuthResult:
    token = extract_bearer_token(request)

    if not token:
        return InternalAPIAuthResult(
            error=InternalAPIAuthError(
                code="internal_api_auth_missing",
                message="Missing internal API bearer token.",
                details={},
            )
        )

    if token.startswith(MCP_USER_TOKEN_PREFIX):
        return _resolve_mcp_user_token_user(
            token,
            required_scopes=required_scopes,
        )

    return _resolve_legacy_internal_api_user(
        token,
    )