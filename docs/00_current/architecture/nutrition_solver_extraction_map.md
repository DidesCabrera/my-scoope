# Nutrition Solver Extraction Map

Status: completed and current

TDG13 retires those temporary import bridges after the last production consumer
migrated to direct `nutrition_solver` imports. Historical S6/S7 sections below retain
the extraction sequence as decision context; they no longer describe import paths
that exist in the current tree.
Date: 2026-07-16
Cycle: NSO00-NSO10
Patch: S10 closure; extended by NSO10 activation and closure

## Optimization V2 current contract

The extracted boundary now optimizes food selection and portion steps rather than only tuning
portions for one preselected set. `OptimizationProblemV2` can express meal slots, meal grammar,
per-meal and daily nutrient ranges, hard constraints, preferences and a deterministic time limit.

The source chain is explicit:

```text
food_catalog.CatalogFood curated capability + confidence
  -> publication snapshot
  -> notas.Food solver_capabilities (stable operational copy)
  -> notas solver profile adapter
  -> pure nutrition_solver OptimizationProblemV2
  -> heuristic_v2 or cp_sat_v1
  -> pending-review NutritionProposal
```

The solver never reads `CatalogFood` at runtime. Catalog facts can improve its functional quality,
but missing optional facts remain diagnosable and can use identified, lower-confidence derivation.

CP-SAT enforces portion bounds/steps, component counts, required functional role groups, explicit
hard food constraints, daily ranges and repetition. It can also produce distinct feasible
compositions. Quality reports expose nutritional proximity and meal-grammar coverage separately.

## Purpose and extraction history

This document records the completed progressive separation of the current nutrition engine into the Django app `nutrition_solver`.

S1 did **not** move code into a new app. S5 created the physical Django app shell. S6 moved pure models/contracts into `nutrition_solver`. S7 moved the deterministic portion solver and strict validators into `nutrition_solver`. S8 added the operational food adapter in `notas`. S9 exposed a controlled AI Assistant preview tool on top of that adapter. S10 creates reviewable solver-generated Meal proposals without applying final changes. TDG13 later retired the temporary compatibility bridges after migrating their last production consumer. The originally planned direct UI step was canceled/differed by decision: users should request solver-backed proposals through `ai_assistant`, not through a dedicated solver UI.

## Current source of truth

The active deterministic solver boundary is split intentionally:

```text
nutrition_solver/
  -> pure contracts, capability profiles, grammar, candidate portfolios,
     heuristic/CP-SAT optimization, validators, quality and diagnostics

notas/application/nutrition_engine/
  -> product-owned target estimation, templates and candidate selection helpers

notas/application/queries/solver_food_candidates.py
  -> ORM adapter from operational notas.Food to pure SolverFood/SolverFoodProfile candidates

notas/application/ai_intake/optimizer_v2_adapter.py
  -> activation adapter and reviewable DailyPlan payload conversion

notas/application/proposals/solver_meal_proposals.py
  -> proposal orchestration and NutritionProposal persistence
```

Current modules:

| Module | Current responsibility | Extraction classification |
|---|---|---|
| `target_estimator.py` | Estimates daily kcal/macros from body/profile/goal inputs and explicit overrides. | Move early; depends only on nutrition constants. |
| `meal_templates.py` | Builds deterministic meal slots, hours, kcal allocations and required roles. | Move early; pure and dependency-light. |
| `candidate_selector.py` | Classifies operational candidates by macro role and preference/exclusion rules. | Move after input candidate contract is stabilized. |

## Current upstream callers

The main current caller is:

```text
notas/application/ai_intake/dailyplan_generator.py
```

That flow turns a nutrition brief into generated daily-plan proposal payloads and
imports deterministic calculation directly from solver-owned contracts.

## App boundary

The future app boundary is:

```text
nutrition_solver
  -> owns deterministic calculation, capabilities required for optimization, constraints,
     meal grammar, backend selection, scoring and diagnostics

notas
  -> owns persisted Food, Meal, DailyPlan, Program and NutritionProposal

food_catalog
  -> owns master/curated catalog and external-source traceability

ai_assistant
  -> owns conversation, provider gateway, tool loop and reviewable proposal UX
```

The solver must not persist operational product entities. It returns structured results; `notas` decides whether those results become reviewable proposals and, later, approved persisted entities.

## Required input boundary

The solver must consume operational candidates derived from `notas.Food`, not catalog/master records.

Allowed source chain:

```text
food_catalog.CatalogFood
  -> explicit snapshot/publication
  -> notas.Food
  -> solver candidate adapter/query
  -> nutrition_solver
```

Disallowed direct solver inputs:

```text
food_catalog.CatalogFood
ExternalFoodReference
FatSecret/Open Food Facts payloads
catalog_food_id/catalog_food_ref
request/user/session/template objects
```

## Contract direction

The extraction must converge toward these concepts:

```text
NutritionTargets
SolverFoodCandidate
SolverConstraint
OptimizationInput
OptimizationResult
OptimizationStatus
OptimizationDiagnostics
```

The existing names may remain temporarily while extraction is prepared:

```text
MacroTarget
SolverFood
PortionBounds
PortionSolverResult
PortionSolverDiagnostics
NutritionValidationIssue
```

S2 introduced explicit optimization-level input/result contracts in `contracts.py` without forcing UI or ORM dependencies into the engine.

## Safe extraction order

1. Keep `notas/application/nutrition_engine` as the canonical implementation.
2. Add docs/tests that freeze the boundary and dependency direction.
3. Introduce optimization-level contracts inside the current engine package. **Completed in S2.**
4. Add tests for serialization, current portion-solver wrapping and impossible results. **Expanded in S3.**
5. Create an empty `nutrition_solver` app only after the contracts are stable. **Completed in S5.**
6. Move pure contracts/models first, preserving compatibility imports from `notas.application.nutrition_engine`. **Completed in S6.**
7. Move solver/validator logic behind adapters. **Completed in S7.**
8. Add a `notas.Food -> SolverFoodCandidate` adapter/query. **Completed in S8.**
9. Let `ai_assistant` preview candidates through a read-only allowlisted tool. **Completed in S9.**
10. Let `ai_assistant` request reviewable solver-generated Meal proposals. **Completed in S10.**
11. Do not create direct solver UI as a cycle requirement; keep user contact through AI Assistant and Proposal Review. **Canceled/deferred by strategic UX decision.**

## Guardrails

- The engine core must remain deterministic and dependency-light.
- The engine core must not import `ai_assistant`, `ai_intake`, `ai_tools`, presentation modules, views, templates or Django request objects.
- The engine core must not import `food_catalog` or external provider payloads.
- The extracted solver core owns its stable nutrition constants and must not import `notas`, `food_catalog` or `ai_assistant`.
- New solver results must include machine-readable diagnostics before they are exposed to AI Assistant or UI.
- Writes must remain reviewable through `NutritionProposal`; solver output is not an approval event.
- The solver should not expose a direct user-facing optimization UI until there is a deliberate product decision to make it a visible surface.

## S1 acceptance criteria

S1 is complete when:

- this extraction map exists under `docs/00_current/architecture/`;
- the planning cycle is marked as active;
- docs explicitly record that no physical app split happens in S1;
- tests protect the documentation contract;
- existing nutrition-engine tests still pass;
- bounded-context tests still pass.


## S2 additions

S2 adds an optimization-level contract module without changing production orchestration:

```text
notas/application/nutrition_engine/contracts.py
```

New contract names:

```text
OptimizationStatus
SolverConstraint
OptimizationInput
OptimizationDiagnostics
OptimizationResult
impossible_optimization_result
```

These contracts wrap the existing `MacroTarget`, `SolverFood`, `SolvedFoodPortion` and `PortionSolverResult` shapes instead of replacing them. This keeps the current `dailyplan_generator` path stable while giving future UI, AI Assistant tools and Proposal Review flows a single machine-readable output vocabulary.

S2 intentionally does not:

- create the physical `nutrition_solver` Django app;
- move solver modules out of `notas`;
- connect the new contracts to ORM, views, templates, requests or provider payloads;
- change the existing portion solver algorithm.

## S2 acceptance criteria

S2 is complete when:

- `contracts.py` exists under `notas/application/nutrition_engine/`;
- contracts expose serializable optimization input/result shapes;
- current `PortionSolverResult` can be wrapped as an `OptimizationResult`;
- impossible solver outcomes can be represented without raising through UI/tool layers;
- docs identify S2 as contract stabilization, not a physical app split;
- existing nutrition-engine tests still pass.


## S3 additions

S3 keeps the implementation inside `notas/application/nutrition_engine/` and adds a thin contract-level adapter:

```text
optimize_meal_portions(OptimizationInput) -> OptimizationResult
```

This adapter is intentionally small. It delegates calculation to the existing deterministic `solve_meal_portions()` function and converts expected impossible inputs into machine-readable `OptimizationResult(status=impossible)` payloads instead of forcing UI, tools or future Proposal Review consumers to catch low-level solver exceptions.

S3 also expands tests for the new contract boundary:

- base solvable meal scenario;
- input warnings such as missing meal slots or soft constraints;
- partial result status when macro deviation is large;
- impossible result for missing candidates;
- impossible result carrying warnings and metadata.

S3 intentionally does not:

- create the physical `nutrition_solver` Django app;
- move modules out of `notas`;
- change the local-search portion solver algorithm;
- connect AI Assistant, UI or MCP/tools to the new wrapper.

## S3 acceptance criteria

S3 is complete when:

- `optimize_meal_portions()` exists as a non-throwing contract-level adapter;
- scenario tests cover base, warning, partial and impossible outcomes;
- optimization result payloads remain JSON-serializable;
- impossible outcomes preserve machine-readable errors, warnings and metadata;
- existing nutrition-engine and bounded-context tests still pass.

## S4 additions

S4 makes the optimization result vocabulary more explicit without changing the physical app boundary.

New contract names:

```text
OptimizationScoringConfig
OptimizationStatusAssessment
assess_optimization_status
```

The solver contract now distinguishes between:

- the raw numeric `score` generated by the deterministic portion solver;
- `score_direction`, currently `lower_is_better`;
- macro-deviation thresholds used to derive status;
- the worst macro deviation that explains the status;
- a machine-readable `reason_code` such as `within_optimal_tolerance`, `within_acceptable_tolerance`, `outside_acceptable_tolerance` or an impossible-result reason.

S4 also adds `issue_counts` to diagnostics so UI, Proposal Review and AI Assistant can quickly distinguish clean results from warning/error-bearing results without parsing free-text arrays.

S4 intentionally does not:

- create the physical `nutrition_solver` Django app;
- move modules out of `notas`;
- change the deterministic portion solver search algorithm;
- connect UI, AI Assistant or MCP/tools to the new status assessment.

## S4 acceptance criteria

S4 is complete when:

- optimization results expose explicit scoring config and score direction;
- diagnostics include a structured status assessment;
- assessments identify the worst macro deviation and threshold used;
- impossible outcomes preserve their reason as assessment `reason_code`;
- result payloads remain JSON-serializable;
- existing nutrition-engine and bounded-context tests still pass.


## S5 additions

S5 creates the physical Django app boundary:

```text
nutrition_solver/
```

The app is registered in `INSTALLED_APPS` as:

```text
nutrition_solver.apps.NutritionSolverConfig
```

S5 intentionally keeps the active deterministic implementation inside:

```text
notas/application/nutrition_engine/
```

The new app shell includes:

```text
nutrition_solver/__init__.py
nutrition_solver/apps.py
nutrition_solver/models.py
nutrition_solver/admin.py
nutrition_solver/migrations/__init__.py
nutrition_solver/tests/
nutrition_solver/README.md
```

S5 intentionally does not:

- move contracts, models, portion solver, validators or target estimation logic;
- add database models;
- connect UI, AI Assistant, MCP/tools or Proposal Review to the new app;
- import `notas`, `food_catalog` or `ai_assistant` from the app shell.

## S5 acceptance criteria

S5 is complete when:

- `nutrition_solver` exists as a physical Django app;
- `NutritionSolverConfig` is registered in `INSTALLED_APPS`;
- the app has README documentation explaining that no production logic moved;
- tests verify importability, app registration and shell guardrails;
- existing nutrition-engine and bounded-context tests still pass.

## S6 additions

S6 begins the physical extraction by moving the pure, dependency-light layer into the new app:

```text
nutrition_solver/domain/models.py
nutrition_solver/application/contracts.py
```

The legacy modules remain as compatibility bridges:

```text
notas/application/nutrition_engine/models.py
notas/application/nutrition_engine/contracts.py
```

Compatibility rules in S6:

- imports from `notas.application.nutrition_engine.models` still resolve to the same classes now owned by `nutrition_solver.domain.models`;
- imports from `notas.application.nutrition_engine.contracts` still resolve to the same pure contracts now owned by `nutrition_solver.application.contracts`;
- `optimize_meal_portions()` remains in the legacy `notas` contracts module because it still delegates to `notas.application.nutrition_engine.portion_solver`;
- `nutrition_solver` pure layers must not import `notas`, `food_catalog` or `ai_assistant`.

S6 intentionally does not:

- move the portion-solver algorithm;
- move target estimation, meal templates, candidate selection or validators;
- connect UI, AI Assistant, MCP/tools or Proposal Review to the new app;
- introduce database models in `nutrition_solver`.

## S6 acceptance criteria

S6 is complete when:

- pure domain models exist under `nutrition_solver/domain/models.py`;
- optimization contracts exist under `nutrition_solver/application/contracts.py`;
- legacy imports from `notas.application.nutrition_engine` remain compatible;
- pure `nutrition_solver` core files do not import `notas`, `food_catalog` or `ai_assistant`;
- existing nutrition-engine tests still pass;
- new nutrition-solver contract tests pass.


## S7 additions

S7 moves the first executable deterministic solver layer into the new app:

```text
nutrition_solver/domain/constants.py
nutrition_solver/application/portion_solver.py
nutrition_solver/application/validators.py
```

The legacy modules remain as compatibility bridges:

```text
notas/application/nutrition_engine/portion_solver.py
notas/application/nutrition_engine/validators.py
notas/application/nutrition_engine/contracts.py
```

Compatibility rules in S7:

- imports from `notas.application.nutrition_engine.portion_solver` still resolve to the same solver config, exception and `solve_meal_portions()` function now owned by `nutrition_solver.application.portion_solver`;
- imports from `notas.application.nutrition_engine.validators` still resolve to the same validator dataclasses and functions now owned by `nutrition_solver.application.validators`;
- `optimize_meal_portions()` now lives in `nutrition_solver.application.contracts` and the legacy `notas` contracts module re-exports it;
- extracted solver application/domain files must not import `notas`, `food_catalog` or `ai_assistant`.

S7 intentionally does not:

- move target estimation, meal templates or candidate selection;
- add the `notas.Food -> SolverFood` adapter;
- connect UI, AI Assistant, MCP/tools or Proposal Review to the new app;
- introduce database models in `nutrition_solver`.

## S7 acceptance criteria

S7 is complete when:

- portion solving exists under `nutrition_solver/application/portion_solver.py`;
- strict validation exists under `nutrition_solver/application/validators.py`;
- legacy imports from `notas.application.nutrition_engine.portion_solver` and `validators` remain compatible;
- `optimize_meal_portions()` resolves from both the new solver app and the legacy `notas` bridge;
- extracted solver files do not import `notas`, `food_catalog` or `ai_assistant`;
- existing nutrition-engine tests still pass;
- new nutrition-solver compatibility tests pass.


## S8 additions

S8 adds the first operational adapter from product persistence into the extracted solver boundary:

```text
notas/application/queries/solver_food_candidates.py
```

The adapter intentionally lives in `notas`, not inside `nutrition_solver`, because it reads `notas.Food`, applies readability/visibility rules and converts ORM rows into pure solver candidates. The extracted solver app remains free of product ORM imports.

Current S8 flow:

```text
notas.Food
  -> get_readable_food_queryset(user)
  -> solver_enabled=True + active + core/extended visibility
  -> build_solver_food_candidate()
  -> nutrition_solver.domain.models.SolverFood
```

The serialized query result must not expose:

```text
catalog_food_id
catalog_food_ref
catalog_snapshot_payload
ExternalFoodReference
provider payloads
```

S8 intentionally does not:

- connect AI Assistant, MCP/tools, Proposal Review or UI;
- move target estimation, meal templates or candidate selection;
- import `notas`, `food_catalog` or `ai_assistant` from `nutrition_solver`;
- introduce database models in `nutrition_solver`.

## S8 acceptance criteria

S8 is complete when:

- a query/adapter can list solver-ready candidates from operational `notas.Food`;
- only active, visible, readable, `solver_enabled=True` foods are returned;
- results are pure `SolverFood` objects and serializable without catalog/external IDs;
- per-food portion bounds are mapped into `PortionBounds`;
- `nutrition_solver` core files remain independent from product apps;
- adapter tests and compatibility tests pass.

## S8 additions

S8 creates the operational food adapter at the correct ORM boundary:

```text
notas/application/queries/solver_food_candidates.py
```

This query reads readable, active and solver-enabled `notas.Food` rows and returns pure `nutrition_solver.domain.models.SolverFood` candidates. It does not expose Food Catalog identifiers, external provider references or raw payloads.

S8 intentionally keeps the adapter outside `nutrition_solver` because the new solver app must not import product ORM, permissions or Food Catalog.

## S8 acceptance criteria

S8 is complete when:

- `notas.Food` rows can be converted into pure `SolverFood` candidates;
- readable/user visibility rules are applied before candidates are returned;
- hidden, inactive or `solver_enabled=False` foods are excluded;
- catalog IDs and provider payloads are not present in serialized candidates;
- `nutrition_solver` still does not import `notas`, `food_catalog` or `ai_assistant`.

## S9 additions

S9 exposes the first AI Assistant read/preview boundary for solver candidates:

```text
ai_assistant tool: preview_nutrition_solver_candidates
```

The tool is read-only and dispatches through the existing AI Assistant allowlist/executor. It calls the S8 adapter indirectly through `notas.application.ai_tools.read_tools.preview_nutrition_solver_candidates_tool`.

The payload is intentionally a preview, not a proposal and not an apply operation:

```text
solver_candidate_preview
source_boundary
```

The preview can include optional `search`, `limit` and `include_extended` arguments. It returns operational `notas.Food` IDs only, shaped as pure solver candidates.

S9 intentionally does not:

- create or apply `NutritionProposal`;
- run a full daily-plan optimization;
- expose Food Catalog fields or external provider payloads;
- import `ai_assistant` from `nutrition_solver`;
- allow writes through the read-only executor.

## S9 acceptance criteria

S9 is complete when:

- the tool registry includes `preview_nutrition_solver_candidates` as a read-only allowlisted tool;
- the read-only executor can dispatch the tool through the local `notas` adapter;
- arguments are normalized and bounded before dispatch;
- tests prove the payload excludes catalog/payload fields;
- existing solver, adapter and AI Assistant registry/executor tests still pass.



## S10 additions

S10 adds the first reviewable proposal write boundary powered by the extracted solver:

```text
ai_assistant proposal tool: create_nutrition_solver_meal_proposal
notas orchestration: notas.application.proposals.solver_meal_proposals
nutrition_solver execution: optimize_meal_portions(OptimizationInput)
```

The orchestration intentionally lives in `notas` because it must read operational food candidates, create a `NutritionProposal` and preserve product ownership rules. The deterministic calculation remains inside `nutrition_solver` and consumes only pure `SolverFood` candidates.

S10 flow:

```text
AI Assistant / internal caller
  -> create_nutrition_solver_meal_proposal
  -> notas.Food candidate adapter
  -> OptimizationInput
  -> nutrition_solver.optimize_meal_portions
  -> create_meal proposed_payload
  -> NutritionProposal(status=pending_review)
```

The generated proposal is still a review artifact. It does not create `Meal`, `MealFood` or `DailyPlan` rows, and it does not approve or apply anything. Approval and application remain separate human-reviewed commands.

The persisted `validation_summary["nutrition_solver"]` includes:

```text
version
status
target
result diagnostics
candidate_preview
source_boundary
```

The source boundary explicitly records that candidates come from `notas.Food`, that the solver receives `nutrition_solver.domain.models.SolverFood`, and that catalog/external payload fields are not exposed.

S10 intentionally does not:

- build a full DailyPlan optimization UI;
- create or apply final Meals automatically;
- expose Food Catalog identifiers or provider payloads;
- let `nutrition_solver` import `notas`, `food_catalog` or `ai_assistant`;
- replace the existing daily-plan generator.

## S10 acceptance criteria

S10 is complete when:

- `create_solver_generated_meal_proposal()` can create a pending-review `NutritionProposal`;
- the proposal payload uses `create_meal` with operational `food_id` values only;
- impossible solver outcomes return an error instead of creating a proposal;
- AI Assistant can dispatch the proposal tool through the reviewable proposal executor;
- validation summary stores structured solver diagnostics and source-boundary guardrails;
- existing adapter, solver and AI Assistant tests still pass.


## Cycle closure

The Nutrition Solver separation cycle closes at S10 + hotfix. The cycle no longer requires the originally planned S11 direct UI because the accepted product boundary is:

```text
Usuario
  -> AI Assistant
  -> allowlisted preview/proposal tools
  -> nutrition_solver deterministic calculation
  -> NutritionProposal pending_review
  -> existing review/apply flow in notas
```

This preserves the solver as an internal deterministic capability and avoids exposing a low-level optimization surface to the user. Future work should improve solver quality, conversational orchestration and Proposal Review explanations instead of adding a direct solver UI by default.

## Closure acceptance criteria

The cycle is closed when:

- `nutrition_solver` is installed as a Django app;
- pure models/contracts and executable portion solving live under `nutrition_solver`;
- `notas` keeps compatibility bridges for legacy imports;
- operational candidate input flows through `notas.Food` adapters only;
- AI Assistant can preview candidates and create reviewable solver-generated Meal proposals;
- solver output creates only `NutritionProposal(status=pending_review)`, not final Meals or applied DailyPlans;
- docs record that direct user UI is canceled/deferred as a strategic product decision.
