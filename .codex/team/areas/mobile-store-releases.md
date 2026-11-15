# Mobile Store Releases

Status: pilot
Owner role: `mobile-store-release-steward`
Last reviewed: 2026-11-14

## Objective

Maintain a traceable, reusable path from approved product scope to mobile-store
review and release, beginning with iOS and App Store Connect.

## Control records

- `mobile-store-releases/release-registry.yaml` tracks intended versions,
  candidates, store status, and closure.
- `mobile-store-releases/readiness-registry.yaml` tracks reusable evidence,
  open gates, and explicit revalidation triggers.
- Historical readiness reviews remain in `.codex/team/memory/projects/`; they are
  evidence inputs, not the current control state.

## Operating boundary

The steward owns release identity, readiness state, evidence reuse, submission
coordination, and the release recommendation. Product, technical, commercial,
legal, finance, and verification authorities retain their domain decisions. No
registry state authorizes an external App Store Connect mutation.

## First pilot evaluation

Answer which product checklist items remain before My Scoope can be sent to App
Review. Recover prior privacy and legal evidence before requesting repetition.
Report a revalidation only when its prior evidence and invalidating trigger are
both identified.
