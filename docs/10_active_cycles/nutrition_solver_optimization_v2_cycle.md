# Nutrition Solver Optimization V2 Cycle

Status: active
Date: 2026-07-16
Cycle: NSO00-NSO10
Branch base: `staging@10cf38f57616ed395f285f892b31361572f1f33c`

## Objective

Evolve Nutrition Solver from a deterministic portion tuner for one preselected food set into
an explainable optimizer that can jointly consider food capabilities, meal structure, candidate
selection, portion steps, daily nutrition and user constraints.

The cycle keeps the accepted safety boundary:

```text
Food Catalog owns curated facts, provenance and confidence.
notas owns stable operational Food snapshots and persistence.
Nutrition Solver owns requirements, constraints, optimization and diagnostics.
AI Assistant orchestrates tools and presents reviewable proposals.
The user reviews and applies; the LLM does not invent final portions.
```

## Hard gates

- One independently reversible commit per NSO patch.
- No direct runtime read from `nutrition_solver` to `food_catalog.CatalogFood`.
- New behavior remains behind an explicit backend or shadow-mode setting until NSO10.
- The current heuristic remains available as a compatibility backend.
- A result that cannot satisfy hard constraints is structured as impossible, never silently relaxed.
- Solver proposals remain `NutritionProposal(status=pending_review)`.
- Focal tests run per patch; global CI must be green before merge to `staging`.

## Baseline

NSO00 freezes the current v2 behavior:

- candidate selection is deterministic and greedy by nutritional role;
- portion solving uses multiple deterministic starts;
- each start performs coarse-to-fine coordinate search with at most 220 improvement rounds;
- the score weighs protein, kcal, carbs and fat plus over/undershoot and optional-food costs;
- status is based on the worst macro deviation with 8% optimal and 18% acceptable thresholds;
- current `OptimizationInput.constraints`, `preferences` and `context` are serializable but are
  not yet fully enforced by the portion solver.

## Patch sequence

| Patch | Deliverable |
| --- | --- |
| NSO00 | Baseline, golden scenarios and execution contract. |
| NSO01 | Explicit Food Catalog-Solver ownership and capability requirements. |
| NSO02 | Versioned food capability contracts and confidence diagnostics. |
| NSO03 | Curated capability fields and Food Catalog readiness. |
| NSO04 | Explicit snapshot propagation into operational `notas.Food`. |
| NSO05 | Optimization Contract V2 and meal grammar. |
| NSO06 | Candidate portfolio and combination-aware planning. |
| NSO07 | CP-SAT backend behind a backend selector. |
| NSO08 | Whole-day optimization and diverse alternatives. |
| NSO09 | Shadow comparison, explanations and quality telemetry. |
| NSO10 | Activation gates, current docs, Knowledge Center and cycle closure. |

## Implementation status

- NSO00: completed; baseline and golden scenarios frozen.
- NSO01: completed; versioned feature requirements distinguish required, optional, missing and
  low-confidence capabilities without importing Food Catalog into the solver.
- NSO02: completed; pure food profiles now carry multi-capability values, provenance, confidence,
  derivation status and schema version without inventing missing data.
- NSO03: completed; Food Catalog can curate multi-role capabilities, affinities, tags, allergens,
  effort, cost and feature confidence while keeping optional data explicitly absent.
- NSO04: completed; capabilities now cross through an explicit, versioned `notas.Food` snapshot
  and become pure solver profiles without exposing master catalog identity.
- NSO05: completed; Optimization Problem V2 adds nutrient ranges, slots and backend-independent
  constraints while meal grammar validates multi-capability archetypes.
- NSO06: completed; bounded candidate portfolios now rank multiple complete meal-grammar
  combinations using capability confidence, affinity, exclusions and explicit preferences.
- NSO07: completed; the selectable CP-SAT backend jointly enforces meal grammar, hard nutrient
  ranges, exclusions, portion bounds and portion steps while preserving the heuristic backend.

## Golden scenario families

- feasible balanced meal;
- optional ingredient may remain at zero;
- explicit portion bounds and steps;
- hard exclusion or missing capability;
- insufficient candidates;
- locally acceptable but daily-improvable composition;
- deterministic repeated execution;
- backend comparison without changing the visible proposal.

## Definition of done

NSO00-NSO10 is complete only when the new backend can run in shadow mode and controlled active
mode, diagnostics expose nutritional and functional quality separately, the current heuristic
remains reversible, docs reflect the durable contract, and CI contains no hard regression.
