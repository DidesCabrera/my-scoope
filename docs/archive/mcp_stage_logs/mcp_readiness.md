# MCP Readiness

This document explains how the current architecture prepares My Scoope for future MCP integration.

## Goal

The long-term goal is to allow external AI agents, such as ChatGPT or other MCP-compatible clients, to interact with My Scoope safely.

The first MCP milestone should not allow agents to directly modify final user plans.

Instead, the target flow is:

```text
AI agent
  -> My Scoope MCP tools
  -> create proposal
  -> My Scoope validates
  -> user reviews
  -> user approves or rejects