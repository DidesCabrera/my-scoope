import argparse
import os

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route

from myscoope_mcp.auth import (
    create_external_mcp_auth_settings,
    create_external_mcp_token_verifier,
    get_mcp_public_url,
)
from myscoope_mcp.protocol_server import (
    SERVER_NAME,
    assert_protocol_tool_surface_is_safe,
    create_mcp_server,
    get_protocol_allowed_tool_names,
)
from myscoope_mcp.well_known import (
    oauth_protected_resource_metadata,
    openai_apps_challenge,
)

DEFAULT_MCP_HTTP_HOST = "127.0.0.1"
DEFAULT_MCP_HTTP_PORT = 8001

STDIO_TRANSPORT = "stdio"
STREAMABLE_HTTP_TRANSPORT = "streamable-http"
HTTP_TRANSPORT_ALIAS = "http"


def _get_default_http_host() -> str:
    return os.getenv(
        "MYSCOOPE_MCP_HOST",
        DEFAULT_MCP_HTTP_HOST,
    )


def _get_default_http_port() -> int:
    raw_port = (
        os.getenv("MYSCOOPE_MCP_PORT")
        or os.getenv("PORT")
        or str(DEFAULT_MCP_HTTP_PORT)
    )

    return int(raw_port)


def _normalize_transport(transport: str) -> str:
    if transport == HTTP_TRANSPORT_ALIAS:
        return STREAMABLE_HTTP_TRANSPORT

    return transport


def _print_registered_tools() -> None:
    print(f"{SERVER_NAME} protocol server initialized safely.")
    print("Registered FastMCP MVP tools:")

    for tool_name in sorted(get_protocol_allowed_tool_names()):
        print(f"- {tool_name}")


def _print_http_runtime_info(
    host: str,
    port: int,
    public_url: str,
) -> None:
    print(f"{SERVER_NAME} HTTP MCP server starting.")
    print(f"MCP endpoint: http://{host}:{port}/mcp")
    print(f"Public MCP URL: {public_url}/mcp")
    print("Well-known endpoints:")
    print(f"- {public_url}/.well-known/openai-apps-challenge")
    print(f"- {public_url}/.well-known/oauth-protected-resource")
    print(f"- {public_url}/.well-known/oauth-protected-resource/mcp")
    print(f"Transport: {STREAMABLE_HTTP_TRANSPORT}")
    print("External MCP auth: enabled")


def _create_http_mcp_server(
    host: str,
    port: int,
):
    public_url = get_mcp_public_url(
        host=host,
        port=port,
    )

    token_verifier = create_external_mcp_token_verifier(
        public_url=public_url,
    )

    auth_settings = create_external_mcp_auth_settings(
        public_url=public_url,
    )

    server = create_mcp_server(
        host=host,
        port=port,
        token_verifier=token_verifier,
        auth_settings=auth_settings,
    )

    return server, public_url


def _create_http_app(server) -> Starlette:
    """
    Return FastMCP's own streamable HTTP app and prepend public well-known routes.

    Important:
    FastMCP's streamable_http_app owns the MCP HTTP lifespan/session manager.
    Wrapping it as a mounted sub-app can break /mcp with runtime 500 errors.
    Therefore we keep the FastMCP app as the top-level ASGI app and insert
    OpenAI Apps discovery/domain-verification routes before the MCP routes.
    """
    if not hasattr(server, "streamable_http_app"):
        raise RuntimeError(
            "This FastMCP version does not expose streamable_http_app(). "
            "Upgrade mcp[cli] or run without well-known support."
        )

    app = server.streamable_http_app()

    well_known_routes = [
        Route(
            "/.well-known/openai-apps-challenge",
            openai_apps_challenge,
            methods=[
                "GET",
            ],
        ),
        Route(
            "/.well-known/oauth-protected-resource",
            oauth_protected_resource_metadata,
            methods=[
                "GET",
            ],
        ),
        Route(
            "/.well-known/oauth-protected-resource/mcp",
            oauth_protected_resource_metadata,
            methods=[
                "GET",
            ],
        ),
    ]

    app.router.routes = [
        *well_known_routes,
        *app.router.routes,
    ]

    return app




def _run_streamable_http_server(
    *,
    server,
    host: str,
    port: int,
) -> None:
    app = _create_http_app(server)

    uvicorn.run(
        app,
        host=host,
        port=port,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the My Scoope MCP protocol server."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Initialize and verify the server without starting the MCP runtime.",
    )
    parser.add_argument(
        "--transport",
        choices=[
            STDIO_TRANSPORT,
            STREAMABLE_HTTP_TRANSPORT,
            HTTP_TRANSPORT_ALIAS,
        ],
        default=os.getenv(
            "MYSCOOPE_MCP_TRANSPORT",
            STDIO_TRANSPORT,
        ),
        help="MCP transport to use. Defaults to stdio.",
    )
    parser.add_argument(
        "--host",
        default=_get_default_http_host(),
        help="HTTP host for remote MCP transport.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_get_default_http_port(),
        help="HTTP port for remote MCP transport.",
    )

    args = parser.parse_args()
    transport = _normalize_transport(args.transport)

    assert_protocol_tool_surface_is_safe()

    if transport == STREAMABLE_HTTP_TRANSPORT:
        server, public_url = _create_http_mcp_server(
            host=args.host,
            port=args.port,
        )

        if args.check:
            _print_registered_tools()
            return

        _print_http_runtime_info(
            host=args.host,
            port=args.port,
            public_url=public_url,
        )

        _run_streamable_http_server(
            server=server,
            host=args.host,
            port=args.port,
        )
        return

    server = create_mcp_server()

    if args.check:
        _print_registered_tools()
        return

    server.run(
        transport=STDIO_TRANSPORT,
    )


if __name__ == "__main__":
    main()