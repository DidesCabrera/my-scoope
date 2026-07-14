# 0044 · Nutrition Solver extraction start

Status: accepted
Date: 2026-07-02

## Context

The Food Catalog launch-readiness cycle is closed. Food Catalog now prepares operational foods for solver use indirectly through `notas.Food`, while keeping master catalog and external provider traceability outside runtime optimization.

My Scoope already has a deterministic nutrition engine inside `notas/application/nutrition_engine/`. It estimates targets, builds meal templates, selects candidates, solves portions and validates macro deviations. This engine is the precursor of the future `nutrition_solver` app.

## Decision

Start the Nutrition Solver separation cycle with a conservative S1 patch.

S1 does not create the `nutrition_solver` Django app and does not move engine files. Instead it records the extraction map, activates the planning cycle, and protects the boundary with tests.

The current implementation remains canonical here:

```text
notas/application/nutrition_engine/
```

The future direction remains:

```text
nutrition_solver calculates and diagnoses.
notas persists and presents.
food_catalog curates and publishes operational snapshots.
ai_assistant interprets intent and uses controlled tools.
```

## Consequences

- The team can continue patching safely without a premature app split.
- Future patches can introduce optimization-level contracts before moving files.
- AI Assistant cannot become the source of truth for final portions.
- Food Catalog remains outside solver runtime inputs except through operational `notas.Food` snapshots.
- The physical app split is deferred until contracts and tests are stable.
