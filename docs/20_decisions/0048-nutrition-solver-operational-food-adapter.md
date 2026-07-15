# 0048 — Nutrition Solver operational food adapter

Date: 2026-07-02
Status: accepted
Cycle: Nutrition Solver separation, Patch S8

## Context

After S6/S7, the pure contracts, deterministic portion solver and validators live under `nutrition_solver`. The next boundary required by the solver cycle is an adapter from operational foods into pure solver candidates.

`nutrition_solver` must not import `notas.Food`, Food Catalog models, external references, AI Assistant or presentation code. At the same time, the system needs a stable way to read foods that are safe for optimization.

## Decision

Create the adapter/query in `notas`:

```text
notas/application/queries/solver_food_candidates.py
```

The adapter reads operational `notas.Food` rows through existing read boundaries and returns pure `nutrition_solver.domain.models.SolverFood` objects.

Allowed input source:

```text
notas.Food
```

Required filters:

```text
readable by user
is_active=True
solver_enabled=True
visibility in core/extended
```

Disallowed output fields:

```text
catalog_food_id
catalog_food_ref
catalog_snapshot_payload
external provider references
raw provider payloads
```

## Consequences

- `nutrition_solver` remains clean and independent from product ORM.
- `notas` owns the ORM/read-boundary adapter because it owns persistence and permissions.
- S9 can build an AI Assistant read/preview tool on top of this query without exposing Food Catalog internals.
- Future role selection can become smarter, but S8 provides a deterministic default role inference and portion-bound mapping.
