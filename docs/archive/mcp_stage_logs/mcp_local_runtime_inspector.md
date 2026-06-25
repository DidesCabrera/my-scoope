# MCP Local Runtime / Inspector Integration

## Purpose

This stage connects the Real MCP Protocol Wrapper to a local MCP client.

The goal is to prove that My Scoope can be called through a real MCP runtime and that an external AI-style client can use the safe tool surface.

The target milestone is:

```text
Django local server
  → MCP Server local runtime
  → MCP Inspector
  → list_user_proposals
  → create_validated_dailyplan_proposal
  → proposal appears in My Scoope
  