# 0046 — Nutrition Solver pure contracts moved

Date: 2026-07-02
Status: accepted
Cycle: Nutrition Solver App Cycle
Patch: S6

## Decision

Move the pure, dependency-light nutrition solver dataclasses and optimization contracts from the legacy `notas.application.nutrition_engine` boundary into the physical `nutrition_solver` app:

```text
nutrition_solver/domain/models.py
nutrition_solver/application/contracts.py
```

Keep compatibility bridges in the old import locations:

```text
notas/application/nutrition_engine/models.py
notas/application/nutrition_engine/contracts.py
```

## Rationale

The solver now has a physical app boundary from S5. S6 should make that boundary meaningful without moving the production algorithm yet. Pure models and contracts are the safest first extraction because they do not require ORM, views, templates, requests, AI provider payloads or external catalog records.

This gives future patches a stable import target while avoiding a disruptive rewrite of the current `dailyplan_generator` and nutrition-engine tests.

## Compatibility rule

Existing imports must continue working during the transition:

```python
from notas.application.nutrition_engine.models import MacroTarget
from notas.application.nutrition_engine.contracts import OptimizationInput
```

Those names now resolve to classes/functions owned by `nutrition_solver`, except for the temporary `optimize_meal_portions()` wrapper. That wrapper stays in `notas.application.nutrition_engine.contracts` until the underlying `portion_solver` is moved in S7.

## Guardrails

- `nutrition_solver.domain` and `nutrition_solver.application` must not import `notas`, `food_catalog` or `ai_assistant`.
- The solver app still defines no database models in S6.
- The portion-solver algorithm remains in `notas` until S7.
- UI, AI Assistant, MCP/tools and Proposal Review are not connected to the new app in this patch.

## Consequences

Positive:

- the new app now owns real pure contracts, not just a shell;
- future patches can move solver functions behind stable imports;
- legacy code remains compatible while extraction continues;
- tests can protect the dependency direction of the new app.

Trade-off:

- there is a temporary bridge layer in `notas.application.nutrition_engine`;
- `optimize_meal_portions()` remains in the old module until the algorithm moves.
