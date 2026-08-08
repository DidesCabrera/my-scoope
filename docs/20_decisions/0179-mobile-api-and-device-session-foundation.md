# 0179 - Mobile API and device-session foundation

Status: accepted
Date: 2026-08-05

## Decision

My Scoope adopts Django Ninja 1.6 for the versioned consumer interface at
`/api/v1/`. The generated OpenAPI document is committed and checked for drift in
CI. Transport code returns a stable `{ok, data, error}` envelope and calls
existing application services and selectors rather than duplicating domain
rules.

Public mobile authentication extends the existing PKCE S256 authorization-code
server with device sessions, 15-minute access tokens and rotating 30-day refresh
tokens. Refresh-token reuse revokes the complete device session. Legacy MCP and
ChatGPT clients remain compatible with their access-only exchange.

## Consequences

- React Native can generate or type-check a client against a stable contract.
- One device can be revoked without logging out every device.
- Access-token theft has a bounded lifetime; refresh reuse has an explicit
  containment response.
- `MCPUserToken` remains the hashed bearer-token persistence mechanism during
  CML02, now optionally linked to a device session.
- New mobile resources must reuse the envelope and scope model.
- Adherence endpoints wait for the CML04 execution model instead of inventing
  transport-owned state.
