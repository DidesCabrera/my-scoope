# AI Assistant Patch + Solver Synergy Cycle

Status: completed
Branch: `refactor/ai-assistant-patch-solver-synergy`
Started: 2026-09-16

## Objective

Turn the assistant from a collection of narrowly selected actions into a capable,
reviewable operator. The model should understand and compose the requested outcome;
My Scoope must retain authority over data, nutrition calculation, permissions,
atomic writes and approval.

## Work stages

| Stage | Outcome | Status |
| --- | --- | --- |
| APS00 | Freeze branch/worktree state and re-audit tool, proposal and solver boundaries. | complete |
| APS01 | Define `ai_assistant_workspace_patch.v1`, risk levels and approval policy. | complete |
| APS02 | Prepare and atomically commit multi-operation patches through existing domain commands. | complete |
| APS03 | Replace the provider-selected mutation micro-tool with `propose_workspace_patch`; keep compatibility. | complete |
| APS04 | Correct optimizer weighting and consume typed dietary, allergen, effort, cost and variety capabilities. | complete |
| APS05 | Generate three ranked solver alternatives by default with safe legacy fallback. | complete |
| APS06 | Let proposal review select a trusted stored alternative and resimulate it. | complete |
| APS07 | Compare solver quality across assistant-driven revisions. | complete |
| APS08 | Update current architecture, decisions, tests and integration evidence. | complete |

## Safety invariants

1. Provider calls may prepare patches but cannot call commit.
2. Patch payloads never contain arbitrary model code, SQL or ORM field paths.
3. Every operation maps to an allowlisted application command and owned target.
4. The complete patch is atomic and rejects stale target snapshots.
5. All version-1 patches require a trusted web/mobile confirmation.
6. Solver alternatives remain pending-review proposal payloads; selecting one does not
   approve or apply the proposal.
7. The solver consumes operational `notas.Food` snapshots, never Food Catalog rows.
8. An explicit allergy or supported dietary pattern is a hard candidate filter.

## Activation and rollback

Default runtime:

```text
NUTRITION_SOLVER_BACKEND=portfolio_v1
NUTRITION_SOLVER_ALTERNATIVE_COUNT=3
```

`portfolio_v1` tries CP-SAT and records any fallback to the legacy generator. A request
with typed dietary/allergen constraints never falls back to the legacy path. To roll
back visible optimization while keeping the new proposal/patch contracts available:

```text
NUTRITION_SOLVER_BACKEND=heuristic_v2
NUTRITION_SOLVER_SHADOW_ENABLED=false
```

The old `prepare_product_action` registration remains available for stored/history
compatibility, but provider selection routes new general mutations to
`propose_workspace_patch`.

## Validation evidence

Repository validation completed on 2026-09-16:

- focused Workspace Patch, solver, proposal-alternative and iteration suites: green;
- mobile iteration gate: lint, TypeScript typecheck and 121 contract/unit tests green;
- Django integration gate: repository hygiene, reviewed debt budgets, framework and
  migration checks, current OpenAPI, strict document registry and 97 architecture
  tests green;
- full Django suite: 1,972 tests green;
- Workspace Patch no longer needs a complexity-budget exception after its commit
  dispatcher was split by domain;
- the standalone complexity audit still reports two inherited hotspots outside this
  change: `apply_preference_draft_to_brief` and `ai_nutrition_intake`.

No migration is required. The generated mobile OpenAPI contract is current.

## Known limits and follow-up work

- Generic patch covers entity/lifecycle commands plus Meal-food and DailyPlan-meal
  composition through existing services. Program composition and sharing are not
  disguised as arbitrary writes.
- The optimizer still chooses the first compatible archetype for each current meal
  template. Multi-archetype search is a later solver improvement.
- Typed allergen and dietary behavior is only as complete as operational capability
  snapshots; missing allergen data fails safe when the user declares an allergy.
- Low-risk auto-apply is only modeled as future eligibility. Enabling it requires a
  separate user autonomy preference, audit decision and rollout.
- Physical staging validation with the real provider remains an operational release
  check, not a repository implementation gap.
