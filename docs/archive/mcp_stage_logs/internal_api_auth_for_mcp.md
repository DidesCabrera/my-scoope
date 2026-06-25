# Internal API Auth for MCP

## Purpose

This stage adds an internal authentication path that allows the My Scoope MCP Server to call the Django AI Tools API Adapter as a configured user.

The goal is to unblock this flow:

    MCP Inspector / External AI
      -> FastMCP Server
      -> MyscoopeAPIClient
      -> Django API Adapter
      -> Internal AI Tools
      -> NutritionProposal

The MCP server can now authenticate without relying on a browser session.

---

## Problem Solved

The Django API Adapter originally depended on Django session authentication.

That works for normal browser users, but the MCP server is not a browser session.

Without internal API auth, MCP calls may reach Django but fail because request.user is anonymous or because Django redirects to login.

This stage adds a second valid authentication path:

    Authorization: Bearer <internal-token>

---

## MVP Auth Strategy

For the local/private MVP, My Scoope supports an internal Bearer token.

Environment variables used by Django:

    MYSCOOPE_INTERNAL_API_TOKEN
    MYSCOOPE_INTERNAL_API_USERNAME

Example:

    MYSCOOPE_INTERNAL_API_TOKEN=dev-mcp-token
    MYSCOOPE_INTERNAL_API_USERNAME=felipe

The MCP server sends:

    Authorization: Bearer dev-mcp-token

The Django API Adapter validates the token and resolves:

    request.user = User(username="felipe")

---

## MCP Server Environment

The MCP server already supports:

    MYSCOOPE_API_BASE_URL
    MYSCOOPE_API_AUTH_TOKEN
    MYSCOOPE_API_TIMEOUT_SECONDS

For local Inspector usage:

    MYSCOOPE_API_BASE_URL=http://127.0.0.1:8000/app
    MYSCOOPE_API_AUTH_TOKEN=dev-mcp-token

The MCP client sends MYSCOOPE_API_AUTH_TOKEN to Django as:

    Authorization: Bearer <token>

The value of MYSCOOPE_API_AUTH_TOKEN in the MCP environment must match MYSCOOPE_INTERNAL_API_TOKEN in the Django environment.

---

## Local Configuration Example

In the Django terminal:

    export MYSCOOPE_INTERNAL_API_TOKEN="dev-mcp-token"
    export MYSCOOPE_INTERNAL_API_USERNAME="felipe"
    python manage.py runserver

In MCP Inspector environment variables:

    PYTHONPATH=mcp_server
    MYSCOOPE_API_BASE_URL=http://127.0.0.1:8000/app
    MYSCOOPE_API_AUTH_TOKEN=dev-mcp-token

Inspector command:

    /Users/felipedides/Desktop/proyecto_django/venv/bin/python

Inspector arguments:

    -m myscoope_mcp.run_protocol_server

Do not use --check in Inspector.

---

## Why Username Instead of user_id

The MCP auth boundary must not accept user_id from the request payload.

Invalid pattern:

    {
      "user_id": 1,
      "dailyplan_id": 123
    }

Correct pattern:

    Authorization: Bearer <configured-token>

The server configuration determines the authenticated user.

This prevents an external client from impersonating another user by changing JSON payload data.

---

## Session Auth Still Works

This internal auth path does not replace normal Django session auth.

Allowed paths:

    Browser session user
      -> request.user is already authenticated

    MCP Bearer token
      -> request.user is resolved from internal configuration

If neither is valid, the API Adapter rejects the request or redirects according to the existing session-login behavior.

---

## Implemented Files

Internal auth helper:

    notas/interface/api/auth.py

API decorator integration:

    notas/interface/api/decorators.py

API response helper:

    notas/interface/api/responses.py

Tests:

    notas/tests/test_ai_tools_api_internal_auth_helper.py
    notas/tests/test_ai_tools_api_internal_auth_integration.py
    notas/tests/test_ai_tools_api_internal_auth_contracts.py

---

## Supported Auth Flow

Expected request flow:

    MCP Server
      -> Authorization: Bearer <token>
      -> ai_tool_api_view decorator
      -> resolve internal API user
      -> request.user
      -> parse JSON
      -> endpoint function
      -> Internal AI Tool
      -> AIToolResult.as_dict()

---

## Error Cases

The implementation handles:

    missing token
    invalid token
    missing configured token
    missing configured username
    configured user does not exist
    inactive user
    malformed Authorization header
    invalid JSON
    non-object JSON
    method not allowed

Errors preserve the API Adapter contract whenever the request is handled as API auth:

    {
      "ok": false,
      "data": {},
      "error": {
        "code": "...",
        "message": "...",
        "details": {}
      }
    }

---

## Stable Error Codes

Internal auth error codes include:

    internal_api_auth_missing
    internal_api_auth_not_configured
    internal_api_auth_invalid
    internal_api_auth_user_not_configured
    internal_api_auth_user_not_found
    internal_api_auth_user_inactive

JSON and method contract errors remain:

    invalid_json
    json_body_must_be_object
    method_not_allowed

---

## Security Boundary

The internal MCP auth layer must not:

    accept user_id as authority
    accept username from payload
    expose apply tools
    bypass Internal AI Tools permissions
    bypass API Adapter contracts
    mutate data directly
    authenticate arbitrary users dynamically
    create users automatically

The internal MCP auth layer may:

    read Authorization Bearer header
    compare it with MYSCOOPE_INTERNAL_API_TOKEN
    resolve a configured user from MYSCOOPE_INTERNAL_API_USERNAME
    attach that user to the request before the AI tool view executes

---

## Product Rule

The product rule remains unchanged:

    MCP can read.
    MCP can validate.
    MCP can create proposals.
    Human reviews.
    My Scoope applies approved changes safely.
    Everything is audited.

MCP must not apply final changes directly.

---

## Current Status

Internal API Auth for MCP is complete when:

    Django accepts Authorization: Bearer <token>
    request.user resolves to the configured user
    list_user_proposals works from MCP Inspector
    read_dailyplan works from MCP Inspector
    compare_dailyplan_to_targets works from MCP Inspector
    create_validated_dailyplan_proposal works from MCP Inspector
    proposal appears in My Scoope
    apply tools remain unavailable
