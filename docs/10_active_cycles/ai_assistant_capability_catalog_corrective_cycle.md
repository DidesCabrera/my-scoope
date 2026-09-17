# AIC00-AIC06 · AI Assistant Capability Catalog Corrective Cycle

Status: implemented in repository; automated staging lab execution pending
Date: 2026-09-17

## Objective

Convert the living request catalog into an honest capability audit and an executable
feedback loop. A capability counts as covered only when the assistant can resolve the
user-visible entity, call an authorized product boundary, preserve conversational
intent, and return facts coherent with the web library.

## Baseline finding

The previous parity cycle classified broad product areas and provided safe read,
proposal, patch and handoff boundaries. It did not prove that every natural-language
request worked end to end. Staging exposed three concrete gaps:

- list tools returned hidden snapshots/drafts and treated an eight-item page as a total;
- a short continuation such as “sí, claro” lost the preceding optimization objective;
- the meal solver could reject an energy-only request without explaining whether the
  failure came from candidates, feasibility or quality.

The catalog remains intentionally mixed: some requests are covered, some are
partial, some belong in specialized UI, and some require new product adapters.

## Stages

### AIC00 — Inventory and honest audit — completed

- Classified 80 initial requests across profile, foods, meals, plans, programs,
  calendarization, proposals/account and analytics.
- Separated deterministic patches from generative proposals and trusted-UI handoffs.
- Kept coverage state explicit instead of treating tool registration as proof.

### AIC01 — Canonical library projections — completed

- Added shared queries for Foods, Meals, DailyPlans and Programs.
- Reused those queries in web list pages and `query_workspace`.
- Excluded inactive foods, drafts, embedded Meals and program-derived DailyPlans from
  the corresponding library collections.

### AIC02 — Complete collection contract — completed

- Added offset pagination and exact `total_count`.
- Added `returned_count`, `has_more`, `next_offset`, `scope` and `resource`.
- Removed the second silent eight-item truncation in provider context while preserving
  the executor's bounded maximum.

### AIC03 — Conversational continuity — completed

- Short acknowledgements use the last operational user message for tool routing.
- The provider still receives the real conversation; this is routing continuity, not
  a fabricated user instruction.
- Regression covers “créame una comida de 450 kcal” followed by “sí, claro”.

### AIC04 — Solver readiness and energy-only requests — completed

- A kcal-only meal request derived the then-current documented target; decision 0198
  subsequently replaced that fallback with 30/50/20.
- Partial macro triples fail clearly.
- Candidate discovery exposes visible, eligible and policy-excluded counts.
- Zero eligible candidates has a stable reason distinct from infeasibility.

### AIC05 — Living catalog gate — completed

- Added a structural contract for all catalog rows; later cycles can extend the count.
- Added a focused CI entry point covering reads, patches, routing, solver and the
  real-provider harness.
- Added a deterministic regression for replacing a food and setting 200 g without
  mutating before confirmation.

### AIC06 — Real-data language validation — ready, external gate pending

- Added `bibliotecas_coherentes` to the explicit real-provider validation catalog.
- It computes expected totals from the selected user's canonical web projections.
- It asks the real model to query each library and fails when visible `TOTAL: N` does
  not match persisted state.
- Running it requires an explicit staging user and consumes configured provider usage.

### AIC07 — Internal evaluation lab — completed in repository

- Added a UI-independent preflight that reads the selected user's canonical library
  projections and solver-ready operational foods.
- Added a deterministic 450 kcal solver probe so candidate absence and mathematical
  infeasibility are known before attributing a failure to the model.
- Bound live cases to catalog IDs for libraries, a 450 kcal meal, an exact 200 g food
  replacement and a 2400 kcal plan with explicit 30/50/20 macros.
- Added before/after state invariants for read-only, proposal-only and prepared-action
  scenarios.
- Added diagnostic grouping for language, routing, tool execution, guardrails, data,
  solver, grounding, provider transport and mutation boundaries.
- Live lab runs clean up only the unconfirmed review artifacts they create unless
  `--keep-artifacts` is requested.

## Deferred risk stage

This cycle does not add program day composition, bulk calendar revisions, sharing,
billing mutations, or new destructive commands to the generic patch vocabulary.
Those operations require a separate threat/risk review, previews that enumerate the
affected objects, and dedicated authorization tests. Existing UI handoffs remain the
safe behavior.

## Validation

Local catalog gate:

```bash
scripts/ci_ai_assistant_capability_catalog.sh
```

Staging language/data gate:

```bash
python manage.py validate_ai_assistant_real_provider \
  --live --user-email usuario@example.com \
  --scenario bibliotecas_coherentes \
  --fail-on-hard-regression
```

Complete internal lab, first without provider calls and then live:

```bash
python manage.py evaluate_ai_assistant_lab --user-email usuario@example.com
python manage.py evaluate_ai_assistant_lab \
  --live --user-email usuario@example.com \
  --output var/ai-evaluation/latest.json \
  --fail-on-regression
```

## Exit criteria

- Web and assistant list/count projections are identical for the four libraries.
- Pagination never presents a page size as the total.
- Deterministic exact edits remain reviewable patches.
- Generative nutrition decisions remain proposals.
- Solver failures identify at least candidate absence separately from infeasibility.
- Every catalog edit must keep the executable structure and focused gate green.
