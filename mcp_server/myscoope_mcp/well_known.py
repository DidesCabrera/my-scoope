import os

from starlette.responses import JSONResponse, PlainTextResponse

from myscoope_mcp.auth import MCP_SCOPE_PROPOSALS_CREATE, MCP_SCOPE_READ
from myscoope_mcp.protocol_server import (
    get_configured_allowed_tool_names,
    get_proposal_tool_names,
)

DEFAULT_MCP_RESOURCE_URL = "https://myscoope-mcp.onrender.com"
DEFAULT_OAUTH_ISSUER_URL = "https://www.myscoope.com"


def get_mcp_resource_url() -> str:
    return os.getenv(
        "MYSCOOPE_MCP_RESOURCE_URL",
        DEFAULT_MCP_RESOURCE_URL,
    ).rstrip("/")


def get_oauth_issuer_url() -> str:
    return os.getenv(
        "MYSCOOPE_OAUTH_ISSUER_URL",
        DEFAULT_OAUTH_ISSUER_URL,
    ).rstrip("/")


def get_protected_resource_scopes() -> list[str]:
    """Advertise only scopes required by the configured MCP tool surface."""
    scopes = [MCP_SCOPE_READ]
    if get_configured_allowed_tool_names().intersection(get_proposal_tool_names()):
        scopes.append(MCP_SCOPE_PROPOSALS_CREATE)
    return scopes


def openai_apps_challenge(request):
    token = os.getenv("OPENAI_APPS_CHALLENGE_TOKEN", "").strip()

    if not token:
        return PlainTextResponse(
            "OPENAI_APPS_CHALLENGE_TOKEN is not configured.",
            status_code=404,
        )

    return PlainTextResponse(
        token,
        status_code=200,
    )


def oauth_protected_resource_metadata(request):
    resource = get_mcp_resource_url()
    issuer = get_oauth_issuer_url()

    return JSONResponse(
        {
            "resource": resource,
            "authorization_servers": [
                issuer,
            ],
            "scopes_supported": get_protected_resource_scopes(),
            "resource_documentation": "https://www.myscoope.com/support/",
        }
    )
