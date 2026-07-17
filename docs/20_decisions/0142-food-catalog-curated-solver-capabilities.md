# 0142 - Food Catalog curated Solver capabilities

Status: accepted
Date: 2026-07-16
Cycle: NSO03

## Decision

Food Catalog stores a compact set of curated solver capabilities: food form, multiple functional
roles, meal affinities, dietary tags, allergens, preparation effort, cost band, schema version
and per-feature confidence. Open lists remain JSON-backed and versioned so future features do not
require an exclusive category hierarchy.

Missing optional capabilities remain empty. Solver readiness warns about absent roles or
affinities but may allow deterministic derivation or neutral behavior later in the operational
adapter.
