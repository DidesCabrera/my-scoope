# MCP Local Environment Setup

## Purpose

This document records the local environment variables needed to let MCP Inspector call My Scoope through the MCP server and Django API Adapter.

---

## Django Terminal

Before running Django locally, export:

    export MYSCOOPE_INTERNAL_API_TOKEN="dev-mcp-token"
    export MYSCOOPE_INTERNAL_API_USERNAME="felipe"

Then run:

    python manage.py runserver

The username must exist in the Django database.

The user must be active.

---

## MCP Inspector Environment

In MCP Inspector, configure environment variables:

    PYTHONPATH=mcp_server
    MYSCOOPE_API_BASE_URL=http://127.0.0.1:8000/app
    MYSCOOPE_API_AUTH_TOKEN=dev-mcp-token

The MCP token must match Django's MYSCOOPE_INTERNAL_API_TOKEN.

---

## Inspector Command

Command:

    /Users/felipedides/Desktop/proyecto_django/venv/bin/python

Arguments:

    -m myscoope_mcp.run_protocol_server

Do not use --check in Inspector.

---

## Manual Verification

Use --check only in the terminal:

    PYTHONPATH=mcp_server python -m myscoope_mcp.run_protocol_server --check

Do not use --check in Inspector.

---

## Expected Real Flow

    MCP Inspector
      -> FastMCP server
      -> MyscoopeAPIClient
      -> Authorization: Bearer dev-mcp-token
      -> Django API Adapter
      -> request.user = felipe
      -> Internal AI Tools

---

## Test Order

1. Start Django with env vars.
2. Start MCP Inspector.
3. Connect Inspector through STDIO.
4. Run list_user_proposals.
5. Run read_dailyplan.
6. Run compare_dailyplan_to_targets.
7. Run create_validated_dailyplan_proposal.
8. Verify proposal in /app/proposals/.

---

## Security Note

This setup is for local/private MVP use.

Do not expose dev-mcp-token publicly.

Before production, replace this with per-user revocable tokens or OAuth-style authorization.
