# 0045 - Nutrition Solver physical app shell

Status: accepted
Date: 2026-07-02
Cycle: `docs/10_active_cycles/nutrition_solver_app_cycle.md`
Patch: S5

## Context

Patches S1-S4 stabilized the future solver extraction path while keeping the active implementation inside:

```text
notas/application/nutrition_engine/
```

The current engine now has explicit optimization-level contracts, scenario tests and status/scoring diagnostics. That makes it safe to create the future Django app boundary without moving business logic yet.

## Decision

Create a physical Django app named:

```text
nutrition_solver
```

Register it in `INSTALLED_APPS` through:

```text
nutrition_solver.apps.NutritionSolverConfig
```

S5 intentionally creates only an app shell:

```text
nutrition_solver/__init__.py
nutrition_solver/apps.py
nutrition_solver/models.py
nutrition_solver/admin.py
nutrition_solver/migrations/__init__.py
nutrition_solver/tests/
nutrition_solver/README.md
```

No production solver logic is moved in S5.

## Rationale

Creating the app shell now gives the project a stable import/install boundary before moving code. This makes later patches smaller and safer because the physical app can be tested independently from the extraction of contracts, solver functions and adapters.

## Guardrails

The S5 app shell must not import:

```text
notas
food_catalog
ai_assistant
```

The active implementation remains in:

```text
notas/application/nutrition_engine/
```

Future extraction should move logic in this order:

```text
contracts/models -> pure solver functions -> adapters -> AI/UI integration
```

## Consequences

- `nutrition_solver` now appears as a real Django app.
- The app has no database models and no migrations beyond the package initializer.
- Tests can assert the app is installed and intentionally empty.
- Existing callers continue using `notas.application.nutrition_engine` until compatibility imports and adapters are introduced.
