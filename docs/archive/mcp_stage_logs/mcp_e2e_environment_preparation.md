# MCP End-to-End Environment Preparation

## Purpose

This document records the local environment required to test the full MCP to My Scoope proposal flow.

The goal is to validate:

    MCP Inspector
      -> FastMCP Server
      -> Django API Adapter
      -> Internal AI Tools
      -> NutritionProposal

---

## Django Environment

Before starting Django locally, export:

    export MYSCOOPE_INTERNAL_API_TOKEN="dev-mcp-token"
    export MYSCOOPE_INTERNAL_API_USERNAME="felipe"

Then run:

    python manage.py runserver

The configured username must exist in the local database.

The user must be active.

---

## Verify Local Users

Use Django shell:

    python manage.py shell

Then:

    from django.contrib.auth.models import User
    User.objects.values("id", "username", "email", "is_active")[:10]

Use the correct username for:

    MYSCOOPE_INTERNAL_API_USERNAME

---

## MCP Server Check

In another terminal:

    PYTHONPATH=mcp_server python -m myscoope_mcp.run_protocol_server --check

Expected tools:

    compare_dailyplan_to_targets
    create_validated_dailyplan_proposal
    list_user_proposals
    read_dailyplan
    read_proposal

---

## MCP Inspector Configuration

Transport:

    STDIO

Command:

    /Users/felipedides/Desktop/proyecto_django/venv/bin/python

Arguments:

    -m myscoope_mcp.run_protocol_server

Environment variables:

    PYTHONPATH=mcp_server
    MYSCOOPE_API_BASE_URL=http://127.0.0.1:8000/app
    MYSCOOPE_API_AUTH_TOKEN=dev-mcp-token

Do not use --check in Inspector.

---

## Token Matching Rule

The MCP environment variable:

    MYSCOOPE_API_AUTH_TOKEN

must match Django's:

    MYSCOOPE_INTERNAL_API_TOKEN

Example:

    MYSCOOPE_API_AUTH_TOKEN=dev-mcp-token
    MYSCOOPE_INTERNAL_API_TOKEN=dev-mcp-token

---

## Expected Result

After this setup:

    MCP Inspector can call the FastMCP server.
    The MCP server can authenticate to Django.
    Django resolves request.user from MYSCOOPE_INTERNAL_API_USERNAME.
    API Adapter tools can run as that user.

---

## Product Boundary

This setup enables MCP to:

    read;
    validate;
    create proposals.

It does not enable MCP to:

    approve proposals;
    apply proposals;
    mutate DailyPlans directly;
    bypass human review.
