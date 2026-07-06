# 0063 · Admin Analytics cycle closure

Status: accepted
Date: 2026-07-04

## Context

The Admin Analytics cycle started after the product architecture reached clearer
boundaries across `accounts`, `ai_assistant`, `food_catalog`,
`nutrition_solver` and `notas`.

The product now needed an internal operating surface: a staff-only dashboard able
to summarize activation, AI usage, account economics, food data quality, solver
quality and operational risks without mixing those responsibilities into any one
domain app.

## Decision

Close the ADM00-ADM10 cycle with `admin_analytics` as a read-first Django app.

The app now exposes:

```text
/staff/analytics/
/staff/analytics/accounts/
/staff/analytics/ai-assistant/
/staff/analytics/product-activity/
/staff/analytics/food-catalog/
/staff/analytics/nutrition-solver/
/staff/analytics/alerts/
```

ADM10 adds final cycle polish:

```text
active internal navigation
Admin Analytics-specific CSS
clear empty-state styling
module map in the executive overview
cycle documentation marked as completed
```

No analytical tables are introduced in this cycle. Metrics continue to be read
from existing operational models through selectors and services.

## Consequences

`admin_analytics` remains a consumer of cross-app signals, not an owner of
commercial, AI, catalog, solver or nutrition-domain behavior.

The system can now answer product-operation questions from a dedicated staff UI:

```text
activation and north-star usage
account plans, credits, wallets and ledger movement
AI usage, cost, status and outcomes
nutrition object activity
food catalog quality and import health
nutrition solver quality signals
internal alerts and health signals
```

Future improvements should be incremental and should preserve the read-first
boundary unless a clear performance or historical-analysis need justifies
snapshots or dedicated analytical tables.
