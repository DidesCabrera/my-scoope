# 0060 · Admin Analytics Nutrition Solver quality metrics

Status: accepted
Date: 2026-07-04

## Context

After ADM06, Admin Analytics can observe Food Catalog quality. The next strategic
need is to see whether Nutrition Solver is producing usable nutrition proposals
and whether the available candidate-food base is ready enough for better solver
results.

`nutrition_solver` is currently an extracted Django app with pure contracts,
portion solving and validators, but it does not own database tables. Solver
quality therefore must be observed through data already persisted by the
proposal review workflow and through readiness fields owned by `notas.Food` and
`food_catalog.CatalogFood`.

## Decision

Add a dedicated staff-only read-first page:

```text
/staff/analytics/nutrition-solver/
```

The page is implemented inside `admin_analytics` and reads existing data through
selectors/services:

```text
NutritionProposal.validation_summary.nutrition_solver
NutritionProposal.validation_summary.engine_validation
NutritionProposal.validation_summary.target_comparison
NutritionProposal.validation_summary.payload_validation
notas.Food solver readiness fields
food_catalog.CatalogFood solver readiness fields
nutrition_solver pure config constants
```

ADM07 does not create models, migrations or analytical snapshots. It preserves
the rule that Nutrition Solver owns optimization/validation contracts while
Admin Analytics consumes persisted outcomes and readiness signals.

## Consequences

Staff can now inspect:

```text
solver summary coverage
optimization status distribution
reason_code and worst_macro diagnostics
average score, iterations and candidate count
strict validation status and issue codes
target macro deviation summaries
operational solver candidate readiness
Food Catalog solver candidate readiness
current solver/validator tolerance configuration
```

The dashboard still does not execute solver runs, tune solver weights, change
candidate selection, apply proposals or modify foods. Those actions remain owned
by their corresponding domain workflows.

## Follow-ups

Future patches can improve this module with explicit solver run logs, named
candidate-selection events, persisted latency per solver run, deeper per-meal
quality scoring and a normalized table for solver outcomes if read-time JSON
aggregation becomes too expensive.
