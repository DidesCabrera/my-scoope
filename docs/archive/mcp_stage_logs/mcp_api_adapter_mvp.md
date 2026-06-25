# MCP/API Adapter MVP

## Purpose

The MCP/API Adapter MVP defines the first external-facing boundary for AI-assisted workflows in My Scoope.

The goal is to expose a small and safe set of AI-oriented capabilities through Django API endpoints before introducing a real MCP server.

This stage is API-first.

The adapter should wrap the Internal AI Tools Layer instead of calling domain models, queries or commands directly.

---

## Strategic Decision: API-first

The first adapter will be implemented as Django API endpoints.

A real MCP server will come later.

This decision keeps the first implementation closer to the current Django monolith and allows the system to reuse existing authentication, request handling, tests and permission boundaries.

The intended direction is:

```text
External client / future MCP
  → API Adapter MVP
  → Internal AI Tools Layer
  → Read Layer / Validation / Proposal Commands
  → Domain