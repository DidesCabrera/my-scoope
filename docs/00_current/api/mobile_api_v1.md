# Consumer Mobile API v1

Status: current
Base path: `/api/v1/`
Interface owner: `mobile_api`

## Contract

The consumer API is a versioned, screen-oriented interface over existing Django
application services. It does not reproduce nutrition, calendarization,
commercial or deletion rules inside transport code.

All product responses use:

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

Errors use the same envelope with `ok=false`, empty `data`, and a stable error
object containing `code`, `message` and `details`.

The generated source of truth is `mobile-v1.openapi.json`. CI regenerates the
schema in memory and fails when the committed contract drifts.

## Authentication

- Public clients use authorization code + mandatory PKCE S256.
- Mobile OAuth clients require an app-generated device identifier and a declared
  platform at token exchange.
- Access tokens expire after 15 minutes.
- Refresh tokens expire after 30 days and rotate on every use.
- Reuse of an already-rotated refresh token revokes the whole device session.
- A user can revoke one device without invalidating unrelated devices.
- Existing MCP/ChatGPT authorization-code clients keep their access-only flow.

Mobile scopes are `mobile:read`, `mobile:write` and `mobile:account`.

## First vertical

The first CML02 vertical exposes health, session, device revocation, profile,
consumer onboarding, account entitlements, active calendarized program, Today,
weight history/write, paginated food search, durable AI submit/poll and account
deletion.

Adherence/execution writes are intentionally absent until CML04 gives them a
durable lived-program model. Food-label capture remains CML05. Food libraries,
meal/daily-plan editing and remaining library mutations can be added after the
React Native execution journey proves they are needed; they must preserve the
same envelope, scopes and service boundaries.
