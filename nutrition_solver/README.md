# Nutrition Solver

Status: portion solver and validators moved in Patch S7.

`nutrition_solver` is the Django app boundary for deterministic nutrition optimization in My Scoope.

At S7, the app owns the first extracted executable solver layer:

```text
nutrition_solver/domain/models.py
nutrition_solver/domain/constants.py
nutrition_solver/application/contracts.py
nutrition_solver/application/portion_solver.py
nutrition_solver/application/validators.py
```

Legacy imports from `notas.application.nutrition_engine.models`, `contracts`, `portion_solver` and `validators` remain available as compatibility bridges while callers migrate progressively.

## Owns now

- pure macro/portion/solver-food dataclasses;
- nutrition energy constants used by the solver;
- optimization input/result/status contracts;
- scoring configuration and status assessment helpers;
- serializable impossible-result payloads;
- deterministic meal portion solving;
- strict validation dataclasses and functions.

## Still owned by `notas` until later patches

- target estimation;
- meal templates;
- candidate selection rules;
- adapters from operational `notas.Food` rows;
- persistence of proposals and applied Meals/DailyPlans/Programs.

## Does not own

- persisted `Food`, `Meal`, `DailyPlan`, `Program` or `NutritionProposal` entities;
- Food Catalog master data or external provider payloads;
- AI Assistant conversation, provider routing or tool loops;
- UI, templates, breadcrumbs or request handling;
- direct writes that bypass Proposal Review.

## S7 guardrail

The extracted solver layers must not depend on `notas`, `food_catalog` or `ai_assistant`. `notas` can depend on `nutrition_solver` through temporary legacy bridges, but the new solver app must stay pure and deterministic.

Compatibility bridges remain in:

```text
notas/application/nutrition_engine/models.py
notas/application/nutrition_engine/contracts.py
notas/application/nutrition_engine/portion_solver.py
notas/application/nutrition_engine/validators.py
```

The extraction order remains:

```text
contracts/models -> pure solver functions -> adapters -> AI/UI integration
```
