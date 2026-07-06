# My Scoope MCP Server

This folder contains the MCP Server and Real MCP Protocol Wrapper for My Scoope.

The MCP server is intentionally separate from the Django app.

## Architecture

```text
MCP Client / External AI
  → FastMCP Protocol Wrapper
  → dispatch_tool_call
  → MCP tool handlers
  → MyscoopeAPIClient
  → Django API Adapter
  → Internal AI Tools Layer
  → Read / Validation / Proposal Layers
  → Domain
```

## Local Runtime / Inspector Integration

The first local runtime target is `stdio`.

This means a local MCP client or Inspector launches the MCP server process and communicates through standard input/output.

Django still runs separately and is reached through HTTP by `MyscoopeAPIClient`.

Expected local flow:

```text
MCP Inspector
  → stdio
  → My Scoope MCP Server
  → HTTP
  → Django API Adapter
```

## Verify Protocol Wrapper

Use check mode to verify that the server initializes and lists the registered tools without starting the blocking MCP runtime:

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.run_protocol_server --check
```

## Food boundary

MCP food tools expose only operational My Scoope Food IDs.

`list_food_catalog` is a historical tool name kept for compatibility. It lists foods available through the Django API Adapter from the operational nutrition layer. It must not be implemented as direct access to the master Food Catalog app, and it must not expose master catalog trace identifiers as food IDs.
