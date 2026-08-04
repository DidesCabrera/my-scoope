import hmac
import os

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

MCP_SCOPE_READ = "myscoope:read"
MCP_SCOPE_PROPOSALS_CREATE = "myscoope:proposals:create"

DEFAULT_MCP_AUTH_SCOPES = [
    MCP_SCOPE_READ,
    MCP_SCOPE_PROPOSALS_CREATE,
]

MCP_USER_TOKEN_PREFIX = "mcp_user_"


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
        self.scopes = list(scopes or DEFAULT_MCP_AUTH_SCOPES)
        self.resource = resource
        self.allow_mcp_user_tokens = allow_mcp_user_tokens

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
            return AccessToken(
                token=token,
                client_id="myscoope-mcp-user-token-client",
                scopes=list(self.scopes),
                resource=self.resource,
            )

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
    required_scopes = list(scopes or DEFAULT_MCP_AUTH_SCOPES)

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

    if token is None:
        raise RuntimeError(
            "MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN is required for streamable-http MCP transport."
        )

    return StaticMCPTokenVerifier(
        expected_token=token,
        scopes=list(scopes or DEFAULT_MCP_AUTH_SCOPES),
        resource=public_url,
        allow_mcp_user_tokens=True,
    )