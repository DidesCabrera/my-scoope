import hmac
import os
import time

import httpx
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

MCP_SCOPE_READ = "myscoope:read"
MCP_SCOPE_PROPOSALS_CREATE = "myscoope:proposals:create"

REQUIRED_MCP_CONNECTION_SCOPES = [
    MCP_SCOPE_READ,
]
LEGACY_MCP_TECHNICAL_SCOPES = [MCP_SCOPE_READ, MCP_SCOPE_PROPOSALS_CREATE]

MCP_USER_TOKEN_PREFIX = "mcp_user_"


def user_tokens_only_enabled() -> bool:
    return os.getenv("MYSCOOPE_MCP_USER_TOKENS_ONLY", "false").strip().lower() in {
        "1", "true", "yes", "on",
    }


class StaticMCPTokenVerifier(TokenVerifier):
    """
    Transitional external MCP auth verifier.

    Supported modes:

    1. Legacy technical token:
       External MCP client
           -> Authorization: Bearer MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN
           -> My Scoope MCP server
           -> Django API with MYSCOOPE_API_AUTH_TOKEN fallback

    2. User token:
       External MCP client
           -> Authorization: Bearer mcp_user_xxx
           -> My Scoope MCP server
           -> Django API with the same mcp_user_xxx token

    The final OAuth version should replace this transitional user-token
    acceptance with proper OAuth-issued access token verification.
    """

    def __init__(
        self,
        expected_token: str,
        scopes: list[str] | None = None,
        resource: str | None = None,
        allow_mcp_user_tokens: bool = True,
    ) -> None:
        self.expected_token = expected_token
        self.scopes = list(scopes or LEGACY_MCP_TECHNICAL_SCOPES)
        self.resource = resource
        self.allow_mcp_user_tokens = allow_mcp_user_tokens

    async def _introspect_user_token(self, token: str) -> AccessToken | None:
        api_base_url = os.getenv("MYSCOOPE_API_BASE_URL", "").rstrip("/")
        if not api_base_url or not self.resource:
            return None

        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                response = await client.post(
                    f"{api_base_url}/ai-tools/mcp-token-introspection/",
                    headers={"Authorization": f"Bearer {token}"},
                )
            if response.status_code != 200:
                return None
            payload = response.json()
        except (httpx.RequestError, ValueError):
            return None

        if not isinstance(payload, dict) or payload.get("active") is not True:
            return None
        if payload.get("resource") != self.resource:
            return None
        scopes = payload.get("scopes")
        expires_at = payload.get("expires_at")
        if (
            not isinstance(scopes, list)
            or not all(isinstance(scope, str) for scope in scopes)
            or not isinstance(expires_at, int)
            or isinstance(expires_at, bool)
            or expires_at <= int(time.time())
        ):
            return None

        return AccessToken(
            token=token,
            client_id="myscoope-mcp-user-token-client",
            scopes=scopes,
            resource=self.resource,
            expires_at=expires_at,
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token:
            return None

        if (
            self.expected_token
            and hmac.compare_digest(token, self.expected_token)
        ):
            return AccessToken(
                token=token,
                client_id="myscoope-external-mcp-client",
                scopes=list(self.scopes),
                resource=self.resource,
            )

        if (
            self.allow_mcp_user_tokens
            and token.startswith(MCP_USER_TOKEN_PREFIX)
        ):
            return await self._introspect_user_token(token)

        return None


def get_external_mcp_auth_token() -> str | None:
    token = os.getenv("MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN")

    if token is None:
        return None

    token = token.strip()

    if not token:
        return None

    return token


def get_mcp_public_url(
    host: str,
    port: int,
) -> str:
    return os.getenv(
        "MYSCOOPE_MCP_PUBLIC_URL",
        f"http://{host}:{port}",
    ).rstrip("/")


def get_mcp_auth_issuer_url(
    public_url: str,
) -> str:
    return os.getenv(
        "MYSCOOPE_MCP_AUTH_ISSUER_URL",
        public_url,
    ).rstrip("/")


def create_external_mcp_auth_settings(
    public_url: str,
    scopes: list[str] | None = None,
) -> AuthSettings:
    issuer_url = get_mcp_auth_issuer_url(public_url)
    required_scopes = list(scopes or REQUIRED_MCP_CONNECTION_SCOPES)

    return AuthSettings(
        issuer_url=AnyHttpUrl(issuer_url),
        resource_server_url=AnyHttpUrl(public_url),
        required_scopes=required_scopes,
    )


def create_external_mcp_token_verifier(
    public_url: str,
    scopes: list[str] | None = None,
) -> StaticMCPTokenVerifier:
    token = get_external_mcp_auth_token()

    if token is None and not user_tokens_only_enabled():
        raise RuntimeError(
            "MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN is required for streamable-http MCP transport."
        )

    return StaticMCPTokenVerifier(
        expected_token="" if user_tokens_only_enabled() else token,
        scopes=list(scopes or LEGACY_MCP_TECHNICAL_SCOPES),
        resource=public_url,
        allow_mcp_user_tokens=True,
    )
