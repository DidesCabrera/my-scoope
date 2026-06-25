# Real MCP Protocol Wrapper

## Purpose

The Real MCP Protocol Wrapper connects the existing My Scoope MCP Server MVP to the actual Model Context Protocol runtime.

The previous MCP Server MVP created:

- tool registry;
- forbidden tool registry;
- HTTP client to the Django API Adapter;
- tool handlers;
- dispatcher;
- manual harness;
- tests.

This stage adds the real MCP protocol layer on top of that dispatcher.

---

## Strategic Rule

The real MCP wrapper must be thin.

Correct flow:

```text
MCP protocol request
  → FastMCP tool
  → dispatch_tool_call
  → tool handler
  → MyscoopeAPIClient
  → Django API Adapter
  → Internal AI Tools