# TDG00-TDG08 · Technical Debt Guardrails & Structural Decomposition

Status: active
Owner: Architecture / Developer Experience
Started: 2026-08-02
Decision: `docs/20_decisions/0159-technical-debt-guardrails-cycle.md`

## Purpose

Reduce accumulated technical debt after a high-growth phase without changing
product behavior, shrinking strategically important modules, or reopening closed
feature cycles.

Food Catalog remains a first-class strategic and operational domain inside Admin
Operations. This cycle improves its internal modularity and maintainability; it does
not reduce its scope, navigation, governance workflows, or operational importance.

## Baseline

- branch: `staging`
- baseline checkpoint: `6d789e3` (`Expand Food Catalog operations workspace`)
- Django checks: green
- migrations: no pending model changes
- document registry: valid
- Django suite: 1,641 tests passing in 254.754 seconds locally
- MCP suite: tracked separately but absent from the authoritative CI gate
- browser suite: 27 Playwright-style tests without a reproducible declared runtime
- current hotspots include Admin Operations, the AI Assistant orchestrator/tool
  registry, duplicated test setup, large feature CSS files and transitional app edges

The wall-clock time is diagnostic evidence from one local machine, not a permanent
contract. CI should compare like-for-like runs before enforcing performance budgets.

## Invariants

1. Product behavior remains unchanged unless a real regression is discovered.
2. Food Catalog remains a principal Admin Operations domain.
3. Existing public imports and URLs receive compatibility facades during splits.
4. Every structural change lands with focused tests before the next extraction.
5. The full Django suite remains required; faster gates supplement it rather than
   replace it.
6. MCP and browser tests become explicit quality surfaces instead of silently living
   outside CI.
7. No provider rollout, billing activation, database redesign or Knowledge Center
   expansion belongs to this cycle.

## Patch sequence

### TDG00 — Baseline and cycle registration — completed

- Consolidate the approved Food Catalog Admin Operations work as an independent
  checkpoint.
- Register scope, metrics, invariants and exit criteria.
- Preserve a clean separation between feature growth and debt reduction.

### TDG01 — Reproducible toolchain and dependency boundaries — completed

- Make authoritative scripts select a project Python interpreter without requiring
  a manually activated virtual environment.
- Separate runtime, development, MCP and browser dependency contracts.
- Add one documented command per supported test surface.

### TDG02 — Complete CI quality surfaces — completed

- Keep a fast Django structural gate and the complete Django gate.
- Add an isolated MCP job with its declared dependencies.
- Make the browser smoke suite runnable with configurable URL, generated test data
  and credentials supplied through the environment.

Repository evidence: the fast structural gate passes 73 tests in approximately four
seconds on the baseline machine, and the isolated clean MCP environment passes 169
tests. Browser dependency/setup ownership is explicit; deterministic fixture and auth
migration remains TDG07 scope.

### TDG03 — Static and architectural debt ratchets — completed

- Add incremental lint and dependency-audit configuration.
- Declare and test cross-app dependency directions and transitional edges.
- Remove the concrete `credits` / `usage` module cycle.
- Prevent Tier 2 service modules from acquiring HTTP response concerns.

Repository evidence: the production import graph has no module cycles; cross-app
edges and the remaining Admin Operations object-lookup exception are executable
ratchets. Ruff's fatal correctness families pass, the complete Django suite passes
1,642 tests against the patched dependency set, and `pip-audit` reports no known
vulnerabilities.

### TDG04 — Admin Operations modular decomposition — completed

- Split services, selectors and viewmodels by `overview`, `food_catalog`, `accounts`,
  `ai_assistant` and `audit` responsibilities.
- Move messages and HTTP object lookup to the interface.
- Keep compatibility exports while callers migrate.

Repository evidence: the former 2,500-line service module is a 12-line compatibility
facade. Services, selectors and view models are owned by overview, Food Catalog,
accounts, AI Assistant and audit modules; all 63 Admin Operations tests pass. The
application-layer HTTP import allowlist is empty. Food Catalog remains the largest
owned service surface by design and retains every workflow and route.

### TDG05 — AI Assistant runtime seam — planned

- Reduce bidirectional implementation knowledge between `ai_assistant` and `notas`.
- Split provider turn coordination, parsing, continuation and fallback policy behind
  the existing orchestrator facade.
- Split provider tool schemas by capability while keeping the canonical registry.

### TDG06 — Test ergonomics and feedback time — planned

- Introduce focused builders for repeated account and nutrition objects.
- Migrate the highest-duplication suites first.
- Record a fast gate separately from the complete regression suite.

### TDG07 — Frontend debt containment — planned

- Establish no-growth budgets for `!important` and oversized feature stylesheets.
- Split Admin Operations and Programs styles along owned component boundaries.
- Replace browser sleeps and persisted local auth state with observable conditions
  and deterministic setup.

### TDG08 — Transition and closure evidence — planned

- Review registered transitional bridges against their explicit exit evidence.
- Remove stale root artifact and manually duplicated test-count metadata where safe.
- Promote durable outcomes into current architecture/testing docs.
- Close with full repository validation and before/after evidence.

## Exit criteria

- every tracked automated test surface has an explicit runnable command and CI owner;
- full Django and MCP suites pass in clean dependency environments;
- browser smoke tests contain no committed credentials or fixed database object IDs;
- no Python module import cycle remains in production code;
- new cross-app dependencies require an explicit policy change;
- Admin Operations application-equivalent modules do not import messages, redirects
  or HTTP shortcuts;
- AI Assistant orchestration hotspots are decomposed behind stable contracts;
- shared test builders reduce repeated setup in the selected high-volume suites;
- CSS debt metrics cannot grow silently;
- document registry, migrations, Django checks and complete regression gates are green.

## Non-goals

- reducing Food Catalog scope inside Admin Operations;
- activating Mercado Pago, OpenFactura, OpenAI credits, Turnstile or Web Push;
- changing nutrition solver rollout behavior;
- redesigning the product UI;
- completing staging/production operational gates owned by other cycles;
- updating `admin_knowledge` or its human-facing content.
