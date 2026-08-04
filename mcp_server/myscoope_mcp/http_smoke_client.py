import argparse
import asyncio
import json
import os
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

DEFAULT_MCP_URL = "http://127.0.0.1:8001/mcp"


def _parse_json_object(raw_value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid JSON object: {exc}"
        ) from exc

    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError(
            "Expected a JSON object."
        )

    return parsed


def _build_headers(token: str | None) -> dict[str, str] | None:
    if token is None:
        return None

    token = token.strip()

    if not token:
        return None

    return {
        "Authorization": f"Bearer {token}",
    }


def _print_tools(tools: Any) -> None:
    print("Available MCP tools:")

    for tool in tools.tools:
        print(f"- {tool.name}")


async def _run_smoke_client(
    url: str,
    tool_name: str | None,
    tool_arguments: dict[str, Any],
    token: str | None,
) -> None:
    headers = _build_headers(token)

    async with streamablehttp_client(
        url,
        headers=headers,
    ) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:
            await session.initialize()

            tools = await session.list_tools()
            _print_tools(tools)

            if tool_name is None:
                return

            print("")
            print(f"Calling MCP tool: {tool_name}")
            print(f"Arguments: {json.dumps(tool_arguments, indent=2)}")

            result = await session.call_tool(
                tool_name,
                tool_arguments,
            )

            print("")
            print("Tool result:")
            print(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smoke test the My Scoope MCP Streamable HTTP endpoint."
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_MCP_URL,
        help="MCP Streamable HTTP endpoint URL.",
    )
    parser.add_argument(
        "--tool",
        default=None,
        help="Optional MCP tool name to call after list_tools.",
    )
    parser.add_argument(
        "--arguments",
        type=_parse_json_object,
        default={},
        help="JSON object with tool arguments.",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN"),
        help="Bearer token for the external MCP server.",
    )

    args = parser.parse_args()

    asyncio.run(
        _run_smoke_client(
            url=args.url,
            tool_name=args.tool,
            tool_arguments=args.arguments,
            token=args.token,
        )
    )


if __name__ == "__main__":
    main()