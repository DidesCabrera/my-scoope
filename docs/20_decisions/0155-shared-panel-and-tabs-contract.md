# 0155 - Shared Panel and Tabs Contract

Status: accepted
Date: 2026-07-19

## Context

Programs used the same visual ideas as Meals and DailyPlans, but repeated the surface and tab styling inside `programs.css`. This made Programs look like an exception even though its differences are primarily domain composition.

## Decision

Declare neutral contracts:

```text
content-panel
content-panel--main
panel-tabs
panel-tab
```

Programs consumes these contracts together with feature classes. The feature classes own week/day/chart layout and behavior; the shared classes own surface and interaction appearance.

Legacy classes remain as aliases while templates migrate progressively.

## Consequences

- Programs is treated as a first-class entity in the shared UI System.
- Equivalent panels and tabs converge visually through one contract.
- Existing JavaScript selectors and appearance remain compatible.
- Removing legacy aliases is deferred until all consumers have migrated and visual regression coverage exists.
