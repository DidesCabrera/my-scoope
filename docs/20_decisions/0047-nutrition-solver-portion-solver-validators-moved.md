# 0047 - Nutrition Solver moves portion solver and validators

Date: 2026-07-02
Status: accepted
Cycle: `docs/10_active_cycles/nutrition_solver_app_cycle.md`
Patch: S7

## Context

After S6, `nutrition_solver` owned pure domain models and optimization contracts, but the executable deterministic algorithm still lived in:

```text
notas/application/nutrition_engine/portion_solver.py
notas/application/nutrition_engine/validators.py
```

That kept the new app as a shell plus contracts, while `notas` still owned the actual solver behavior.

## Decision

Move the first executable deterministic solver layer into `nutrition_solver`:

```text
nutrition_solver/domain/constants.py
nutrition_solver/application/portion_solver.py
nutrition_solver/application/validators.py
```

Keep compatibility bridges in the legacy paths:

```text
notas/application/nutrition_engine/portion_solver.py
notas/application/nutrition_engine/validators.py
notas/application/nutrition_engine/contracts.py
```

`optimize_meal_portions()` now lives in `nutrition_solver.application.contracts`; the legacy `notas` contracts module re-exports it.

## Consequences

- `nutrition_solver` now owns pure contracts plus the deterministic portion-solving and strict-validation logic.
- Existing callers can continue importing from `notas.application.nutrition_engine.*` during the migration window.
- The extracted solver application/domain files must not import `notas`, `food_catalog` or `ai_assistant`.
- Target estimation, meal templates, candidate selection and operational adapters remain in `notas` until later patches.

## Non-goals

S7 does not connect the solver to UI, AI Assistant, MCP/tools or Proposal Review. It also does not introduce database models in `nutrition_solver`.
