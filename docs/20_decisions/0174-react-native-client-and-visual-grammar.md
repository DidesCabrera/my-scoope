# 0174 React Native client and visual grammar

Status: accepted
Date: 2026-08-05

## Context

The Django product has an established card-based visual language, semantic tokens
and shared presentation components, but its implementation is HTML/CSS and cannot
be reused directly by a native client. A remote PWA wrapper would also fail to
deliver the intended daily mobile experience.

## Decision

The consumer mobile client uses stable React Native with TypeScript and an Expo
development build. It consumes a versioned Django API and may add bounded native
modules for Apple platform capabilities.

Before feature screens are built, CML03 inventories the existing UI grammar and
promotes its durable colors, typography, spacing, radii, states and card hierarchy
to a platform-neutral contract. React Native implements native primitives and
domain cards from that contract. Django templates and CSS remain web-owned.

## Consequences

- Product rules remain server-owned.
- Native screens are intentionally redesigned around the daily consumer journey;
  view-for-view parity is not a requirement.
- Visual continuity is reviewable without forcing pixel parity or a simultaneous
  web CSS rewrite.
- Development builds are required from the beginning because OCR, StoreKit and
  notification work needs native configuration.
