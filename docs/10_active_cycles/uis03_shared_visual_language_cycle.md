# UIS03 — Shared Visual Language Cycle

Status: completed
Date: 2026-07-19
Cycle code: UIS03
Scope: UI contract and component taxonomy

## Objective

Make explicit that Programs is a domain composition of the same UI System used by Foods, Meals and DailyPlans.

## Decision

```text
Programs may have domain-specific composition.
Programs does not have domain-specific visual primitives.
```

Panels, tabs, cards, data grids, actions and empty states must use the shared contracts. Feature classes may control internal layout, JS behavior or bounded variants only.

## Delivered

- Added `content-panel`, `content-panel--main`, `panel-tabs` and `panel-tab` to the official taxonomy.
- Defined legacy aliases for progressive adoption.
- Corrected the Programs contract in the UI System and component inventory.
- Defined a migration rule that preserves appearance and behavior.

## Acceptance

- The current contract no longer describes Programs as an independent visual family.
- New Programs panels and tabs have a clear shared component to consume.
- Migration does not require a big-bang rewrite.
