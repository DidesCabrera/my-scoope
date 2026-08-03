# Nutrition Solver

Status: Optimization V2 implementation complete in NSO00-NSO10.

`nutrition_solver` is the Django app boundary for deterministic nutrition optimization in My Scoope.

The app owns both the compatible deterministic portion solver and Optimization V2:

```text
nutrition_solver/domain/models.py
nutrition_solver/domain/constants.py
nutrition_solver/application/contracts.py
nutrition_solver/application/portion_solver.py
nutrition_solver/application/validators.py
nutrition_solver/application/problem_v2.py
nutrition_solver/application/candidate_portfolio.py
nutrition_solver/application/optimizer_v2.py
nutrition_solver/application/quality.py
nutrition_solver/application/shadow.py
```

The temporary compatibility bridges in `notas.application.nutrition_engine` have
been retired. Product callers import solver-owned contracts and implementations
directly from this app.

## Owns now

- pure macro/portion/solver-food dataclasses;
- nutrition energy constants used by the solver;
- optimization input/result/status contracts;
- scoring configuration and status assessment helpers;
- serializable impossible-result payloads;
- deterministic meal portion solving;
- strict validation dataclasses and functions.
- versioned food capability profiles with confidence and provenance;
- meal grammar and bounded combination-aware candidate portfolios;
- selectable `heuristic_v2` and deterministic `cp_sat_v1` backends;
- per-meal and whole-day hard ranges, portion steps, repetition and distinct alternatives;
- nutritional/functional quality reports and shadow regression comparisons.

## Still owned by `notas` until later patches

- target estimation and legacy meal templates;
- adapters from operational `notas.Food` rows;
- persistence of proposals and applied Meals/DailyPlans/Programs.

`notas/application/ai_intake/optimizer_v2_adapter.py` is the activation boundary. It reads
only solver-enabled operational Food snapshots, constructs a pure Optimization Problem V2 and
converts the result into a reviewable DailyPlan proposal payload.

## Does not own

- persisted `Food`, `Meal`, `DailyPlan`, `Program` or `NutritionProposal` entities;
- Food Catalog master data or external provider payloads;
- AI Assistant conversation, provider routing or tool loops;
- UI, templates, breadcrumbs or request handling;
- direct writes that bypass Proposal Review.

## Runtime selection

| Setting | Default | Purpose |
| --- | --- | --- |
| `NUTRITION_SOLVER_BACKEND` | `heuristic_v2` | Keeps the existing generator visible; set `cp_sat_v1` for controlled activation. |
| `NUTRITION_SOLVER_SHADOW_ENABLED` | `false` | Runs comparison without changing the visible legacy payload. |
| `NUTRITION_SOLVER_SHADOW_BACKEND` | `cp_sat_v1` | Selects the comparison backend. |
| `NUTRITION_SOLVER_TIME_LIMIT_MS` | `1500` | Bounds execution between 50 and 10,000 ms. |

Rollback is configuration-only: restore `NUTRITION_SOLVER_BACKEND=heuristic_v2` and disable shadow
mode. Impossible hard constraints never fall back silently.

## Guardrail

The extracted solver layers must not depend on `notas`, `food_catalog` or
`ai_assistant`. Product adapters may depend directly on `nutrition_solver`, while
the solver app stays pure and deterministic.

The dependency direction remains:

```text
contracts/models -> pure solver functions -> adapters -> AI/UI integration
```
