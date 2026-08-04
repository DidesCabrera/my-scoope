import os

from starlette.responses import JSONResponse, PlainTextResponse

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
            "scopes_supported": [
                "myscoope:read",
                "myscoope:proposals:create",
            ],
            "resource_documentation": "https://www.myscoope.com/support/",
        }
    )