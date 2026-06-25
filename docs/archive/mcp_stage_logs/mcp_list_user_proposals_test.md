# MCP list_user_proposals Real Tool Test

## Purpose

This document records the real local test for the MCP tool:

    list_user_proposals

The goal is to verify that MCP Inspector can call the My Scoope MCP server and route a real tool call toward the Django API Adapter.

---

## Local Services

Django must be running:

    python manage.py runserver

Expected base URL:

    http://127.0.0.1:8000/app

MCP Inspector must be running:

    npx @modelcontextprotocol/inspector

---

## Inspector Configuration

Transport:

    STDIO

Command:

    /Users/felipedides/Desktop/proyecto_django/venv/bin/python

Arguments:

    -m myscoope_mcp.run_protocol_server

Environment variables:

    PYTHONPATH=mcp_server
    MYSCOOPE_API_BASE_URL=http://127.0.0.1:8000/app

Do not use --check in Inspector.

---

## Tool

Tool name:

    list_user_proposals

Arguments:

    {}

---

## Expected Successful Response

A successful response preserves the My Scoope ok/data/error contract:

    {
      "ok": true,
      "data": {
        "proposals": []
      },
      "error": null
    }

If proposals exist, the proposals list may contain objects.

---

## Possible Authentication Response

If the Django API Adapter rejects the MCP request because there is no browser session or internal token auth, the tool may return an error.

This does not mean that MCP failed.

It means the call reached the Django boundary and the next required work is MCP to Django authentication.

Possible errors include:

    api_invalid_json_response
    api_http_error
    api_connection_error

---

## Interpretation

If Inspector can run list_user_proposals and receives an ok/data/error response from the MCP server, the MCP local runtime is working.

If the error is authentication-related, the next required stage is:

    Internal API Auth for MCP

The MCP tool itself remains correctly wired through:

    Inspector
      -> FastMCP
      -> dispatch_tool_call
      -> MyscoopeAPIClient
      -> Django API Adapter

---

## Status

This test validates the first real MCP tool call path.

It does not yet validate proposal creation.
