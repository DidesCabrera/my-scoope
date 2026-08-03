# TDG09-TDG14 · Priority Technical Debt Closure

Status: completed
Owner: Architecture / Developer Experience
Started: 2026-08-02
Decision: `docs/20_decisions/0167-priority-technical-debt-closure.md`

## Purpose

Close the highest-priority debt left after TDG00-TDG08 plus the two approved
transitional bridges. This cycle preserves product behavior and the strategic
scope of Food Catalog while removing runtime coupling and making browser and
account migrations executable.

## Baseline

- branch: `staging`
- baseline checkpoint: `40d18b9` (`Wait for Django before browser smoke`)
- pull request: `#19`, `staging` into `main`
- all GitHub Actions checks green at cycle start
- AI orchestrator: 2,280 lines
- AI Assistant production imports from `notas`: 22 exact allowlisted statements
- authenticated browser scenarios require externally seeded IDs and credentials
- CI runs the same workflow for both a `staging` push and its pull request
- four `notas.application.nutrition_engine` compatibility modules remain; the
  production daily-plan generator is their last product consumer
- `notas.Profile.plan` remains a runtime fallback for account subscriptions,
  entitlements and credit-plan resolution

## Invariants

1. Provider behavior, tool policy, prepared actions and review requirements remain
   compatible while orchestration is extracted.
2. `ai_assistant` must have zero production imports from `notas`; product bindings
   are registered through typed ports owned by the AI application boundary.
3. Authenticated E2E data is ephemeral, deterministic and contains no real secret.
4. Every historical `Profile.plan` assignment is copied into an accounts-owned plan
   and subscription before the field is removed; the migration is reversible.
5. Nutrition solver ownership remains in `nutrition_solver`; `notas` retains only
   product adapters that genuinely use ORM/product policy.
6. The full Django, MCP, quality and browser surfaces remain required.

## Patch sequence

### TDG09 — Registration and executable baseline — completed

- Register scope, invariants and exit criteria.
- Capture the exact transitional imports and migration consumers.

### TDG10 — Provider-turn coordination seam — completed

- Extract the provider turn loop from the orchestrator facade.
- Extract tool-selection/readiness policy behind stable delegation methods.
- Preserve public and test-facing orchestrator behavior.

### TDG11 — AI product ports — completed

- Introduce typed product dispatch/readiness ports in `ai_assistant`.
- Register product implementations from the product composition side.
- Move prepared-action product persistence behind the same boundary.
- Reduce the AI→`notas` allowlist and dependency edge to zero.

### TDG12 — Deterministic authenticated browser CI — completed

- Add an idempotent command that seeds an ephemeral browser user and owned objects.
- Run anonymous and authenticated scenarios in CI using emitted fixture identifiers.
- Remove duplicate push/PR workflow executions for the same proposed change.

### TDG13 — Nutrition solver bridge retirement — completed

- Migrate the final production consumer to direct `nutrition_solver` imports.
- Remove the four legacy compatibility modules and their compatibility-only tests.
- Retire the registered transition after boundary/regression evidence passes.

### TDG14 — Account plan fallback retirement and closure — completed

- Copy legacy plan capabilities into accounts-owned plans/subscriptions in a
  reversible data migration.
- Remove `Profile.plan` and all runtime fallback logic.
- Close transitions and run the complete repository validation.

## Exit criteria

- orchestrator coordination and tool-selection policy are owned outside the facade;
- `ai_assistant` has no production imports from `notas` and no transitional edge;
- authenticated browser scenarios run as a required clean CI gate;
- one proposed change produces one CI workflow execution;
- repository search finds no legacy nutrition solver imports or bridge modules;
- `Profile.plan` is absent and every migrated profile has an accounts subscription;
- forward/reverse migration tests, fast/full Django, MCP, quality and browser gates pass;
- transition and decision registries describe only current boundaries.

## Closure evidence

- stable orchestrator facade reduced from 2,280 to 1,831 lines; provider-turn
  coordination and tool selection are independently owned;
- AI Assistant production imports from `notas`: 22 → 0;
- Django fast: 80 passed; complete Django: 1,649 passed;
- AI Assistant: 220 passed; focused migration/solver/seed: 55 passed;
- MCP: 169 passed; browser: 27 passed; static/security quality: passed;
- reversible `Profile.plan` migration and clean-database forward migration passed;
- the AI/product, solver bridge and account-plan fallback transitions were removed
  from the current registry;
- closure decision: `docs/20_decisions/0168-priority-technical-debt-closure.md`.

## Non-goals

- reducing Food Catalog scope;
- changing provider prompts or product tool capabilities;
- activating external billing, email, Web Push or provider credentials;
- removing the legacy `notas.Plan` table when no consumer requires that separate step;
- updating the Knowledge Center.
