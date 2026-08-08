# 0180 - Expo mobile shell and secure session client

Status: accepted
Date: 2026-08-05

## Decision

The CML03 consumer client lives in `mobile/` on stable Expo SDK 57, React Native
0.86 and Expo Router. It uses a development build from the start. OAuth
authorization code + PKCE runs in the system browser; access and rotating refresh
tokens are persisted with native SecureStore and are never placed in ordinary
application storage.

The client consumes CML02 through one session manager and typed screen-facing
contracts. Its visual primitives consume the platform-neutral
`myscoope.visual-grammar.v1` JSON contract. CI runs lint, strict TypeScript,
session/contract tests and a Metro web export without requiring Apple signing.

## Consequences

- Future camera, notification and StoreKit modules can enter the existing
  development build instead of forcing a later client migration.
- Device-session rotation and revocation remain testable without rendering UI.
- Login, nutrition onboarding, Today and weight are executable against a
  configured environment.
- Check-in interaction is visible but deliberately non-persistent until CML04
  creates execution evidence owned by `ProgramCalendarization`.
- A physical iOS proof still requires Xcode, signing, a reachable HTTPS staging
  deployment and a registered mobile OAuth callback.
