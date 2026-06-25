# MCP Inspector Connection

## Purpose

This document explains how to connect MCP Inspector to the My Scoope MCP server.

This stage verifies that the local MCP runtime can be launched by a real MCP client and that the expected tools are visible.

It does not yet validate end-to-end Django calls.

---

## Prerequisite

Verify the MCP server initializes correctly:

    PYTHONPATH=mcp_server python -m myscoope_mcp.run_protocol_server --check

Expected output:

    my-scoope-mcp protocol server initialized safely.
    Registered FastMCP MVP tools:
    - compare_dailyplan_to_targets
    - create_validated_dailyplan_proposal
    - list_user_proposals
    - read_dailyplan
    - read_proposal

Expected tools:

    compare_dailyplan_to_targets
    create_validated_dailyplan_proposal
    list_user_proposals
    read_dailyplan
    read_proposal

---

## Run MCP Inspector

From the project root:

    npx @modelcontextprotocol/inspector

Open the Inspector UI in the browser.

Default UI URL is commonly:

    http://127.0.0.1:6274

---

## Inspector Configuration

Use:

    Transport Type: STDIO
    Command: /Users/felipedides/Desktop/proyecto_django/venv/bin/python
    Arguments: -m myscoope_mcp.run_protocol_server

Environment variables:

    PYTHONPATH=mcp_server
    MYSCOOPE_API_BASE_URL=http://127.0.0.1:8000/app

If Inspector provides a Working Directory field, use:

    /Users/felipedides/Desktop/proyecto_django

If the Working Directory field is not visible, keep using the absolute Python command and the PYTHONPATH=mcp_server environment variable.

Do not use `--check` in Inspector.

Inspector must launch the real stdio server.

---

## Expected Result

After pressing Connect, go to:

    Tools

Then run:

    List Tools

The expected tools are:

    list_user_proposals
    read_dailyplan
    read_proposal
    compare_dailyplan_to_targets
    create_validated_dailyplan_proposal

---

## Important Notes

The plain terminal command without --check is not a manual check command.

This command is meant to be launched by Inspector:

    PYTHONPATH=mcp_server python -m myscoope_mcp.run_protocol_server

If run directly in a terminal, it waits for an MCP client.

That is expected.

Use this command for manual verification:

    PYTHONPATH=mcp_server python -m myscoope_mcp.run_protocol_server --check

---

## Current Status

The Inspector connection was validated successfully when:

    Connect succeeded.
    Tools were visible.
    Tool List returned the expected MCP tools.

This confirms that the local MCP runtime can be launched by a real MCP client.
