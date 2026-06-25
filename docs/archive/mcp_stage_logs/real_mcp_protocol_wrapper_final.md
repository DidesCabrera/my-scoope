# Real MCP Protocol Wrapper — Final Documentation

## Purpose

The Real MCP Protocol Wrapper connects My Scoope's MCP Server MVP to the actual MCP SDK boundary.

The wrapper exposes My Scoope's safe AI capabilities through FastMCP while preserving the existing architecture:

```text
MCP Client / Inspector / External AI
  → FastMCP Protocol Wrapper
  → dispatch_tool_call
  → MCP tool handlers
  → MyscoopeAPIClient
  → Django API Adapter
  → Internal AI Tools
  → Read / Validation / Proposal Layers