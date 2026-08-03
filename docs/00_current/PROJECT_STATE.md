# Project State - My Scoope

Status: current
Last updated: 2026-08-02
Audience: developers and AI assistants

## What My Scoope is

My Scoope is a Django product for building, managing and evolving nutrition programs, food libraries, meals, daily plans, AI-assisted proposals and internal operational dashboards.

The product is evolving from a monolithic `notas` origin toward clearer app boundaries, with AI-assisted workflows, food catalog governance, nutrition solving, account plans/credits and internal admin tooling.

## Current product posture

My Scoope is past the first architecture-expansion phase. The current priority is operational confidence:

- staging must stay green;
- production changes must flow from local `staging` work to pushed `staging`, then PR
  from `staging` to `main`, then merge and production verification;
- patches should be small and reviewable;
- tests should protect regressions and rules without blocking healthy UI evolution;
- docs should guide decisions without becoming a flat context dump;
- admin tooling should support operation, not just raw database editing.

## App responsibility map

| Area | Responsibility |
| --- | --- |
| `notas` | Legacy/product core for operational nutrition entities such as foods, meals, plans, programs and proposals while extraction continues. |
| `accounts` | User/account domain, onboarding ownership, commercial plans, subscriptions, credits and entitlements. |
| `billing` | Provider-neutral payment and tax-document integration boundary; projects verified commercial state into `accounts`. |
| `email_delivery` | Durable outbound-email attempts, share-email policy, idempotency and operational consumption controls. |
| `ai_assistant` | Chat experience, LLM provider integration, tool orchestration, guarded proposal creation and AI usage observability. |
| `food_catalog` | Master food catalog, import/curation workflows, source governance and controlled bridge toward operational foods. |
| `nutrition_solver` | Deterministic nutrition optimization, meal grammar, constraints, alternatives, quality diagnostics and backend selection, without being a direct user UI. |
| `admin_analytics` | Strategic, read-first product intelligence dashboard for staff. |
| `admin_operations` | Operational staff console for action-oriented workflows, separated from strategic analytics and raw Django Admin. |
| `core` | Cross-cutting technical concerns such as rate limits, shared contracts and regression boot checks. |

## Current architecture principles

- Keep domain rules outside templates and thin views when possible.
- Prefer services, commands and viewmodels over growing legacy views.
- Treat app boundaries by maturity: mature apps should be stricter; transitional legacy areas can use pragmatic bridges.
- AI tools should be allowlisted, observable and proposal-first for writes.
- AI orchestration owns product-facing ports and does not import `notas`; product
  implementations register their bindings from the composition side.
- AI Assistant behavior should favor LLM freedom through typed tool contracts over prompt over-structuring or deterministic conversational guards.
- Behavioral alignment should direct the assistant through product purpose, current state, capabilities and boundaries rather than fixed dialogue scripts.
- User-visible credits are product/account concepts; provider tokens and costs are internal observability concepts.
- `accounts.AccountPlan` and `AccountSubscription` are the sole runtime authority
  for commercial entitlements; `Profile.plan` no longer exists.
- External payment evidence and tax-document lifecycle belong to `billing`; verified outcomes project into `accounts`, which remains the entitlement source of truth.
- Cross-app dependencies, transitional adapters and production module cycles are
  executable quality contracts rather than informal conventions.
- Admin Operations services, selectors and view models are owned by operational
  domain. Food Catalog remains its principal and intentionally broad domain surface.
- Food Catalog is the master/curation layer; operational `notas.Food` remains the runtime snapshot consumed by existing flows.
- Nutrition Solver should provide reusable calculation/validation capability, mainly through AI Assistant and backend integrations.
- Nutrition Solver consumes versioned capability snapshots from operational `notas.Food`; Food Catalog
  owns curated values/provenance and is never a live solver dependency.

## Testing posture

The current testing baseline is intentionally pragmatic:

- protect boot/import/URL/config regressions;
- add regression tests for real bugs that reached CI/staging/local dev;
- prioritize domain and integration tests for durable business rules;
- keep UI tests as smoke/render/permissions tests only;
- avoid brittle tests that lock CSS classes, exact HTML structure, decorative copy or component counts.

CI should reduce manual testing of technical boot issues. Manual testing remains important for product experience, mobile behavior, OAuth provider behavior and staging sanity checks.

For visual-only, copy-only or docs-only changes, avoid unnecessary full-suite churn:
keep the patch narrow, document why local full tests were skipped, use the
`staging` -> PR -> `main` workflow, and verify production or report the deployment
blocker before considering the task done.

## Documentation posture

`docs/` must be read as a hierarchy, not a flat folder.

- `docs/00_current/AI_README.md` is the AI entrypoint.
- `docs/00_current/` is the current source of implementation truth.
- `docs/20_decisions/` explains accepted rationale and history.
- `docs/10_active_cycles/` prepares cycles but does not override current contracts.
- `docs/90_archive/` is historical context only.

Project control is also executable:

- `diagnose_environment` reports sanitized environment and integration readiness;
- `project_status` reports release, migrations, capabilities and safe aggregates;
- Admin Operations > Project Control renders the same contract as a staff-only,
  read-only surface;
- `ai_project_context` composes current status, live cycles, decisions, transitions and
  product bets for AI clients without private rows or secret values.

When a plan becomes real, durable outcomes should be promoted into `docs/00_current/` and decisions should be recorded in `docs/20_decisions/`.

## Recently closed baselines

- Email delivery abuse-protection baseline: server-validated Turnstile integration,
  multi-window signup limits, shared-cache production path, auditable account email,
  idempotent/budgeted share invitations and a non-critical email kill switch.
- Calendarization repository baseline: a user-owned weekly program can be activated on
  real dates as immutable daily snapshots, with one current schedule, IANA timezone and
  configurable local notification time. Daily and per-meal Web Push use persisted
  logical events and idempotent per-device deliveries behind a kill switch. Production
  activation still requires VAPID credentials, a five-minute scheduler and staging smoke.

- CI/staging stabilization and test hygiene baseline.
- Rate-limit dependency alignment for login/signup flows.
- Admin Operations V1 as an operational staff console.
- Admin Analytics as a strategic staff dashboard.
- Account plans/credits ownership moved toward `accounts`.
- Billing BILL00-BILL09 separates Mercado Pago collection, account entitlements and OpenFactura DTEs; checkout, signed webhooks, idempotent issuance, reconciliation, reversals and operations queues are implemented while real traffic remains disabled pending sandbox and accounting gates.
- Nutrition Solver separation baseline.
- Food Catalog launch-readiness cycle.
- AI Assistant activation/observability/credits guardrails.
- AI Assistant Client Memory & Profile Objects and LLM-native alignment cycle CM00-CM24. The final real-provider gate and targeted UX rerun passed automated and human review, consolidating native function calling, grounded state transitions and explicit cards.
- AI Assistant Behavioral Alignment BA00-BA07 and Post-Tool Follow-up Transport PT00-PT06 are closed. The accepted baseline covers domain anchoring, capability abstraction, ambiguous-intent restraint, goal-directed progression, response quality, exact provider call correlation, contract-faithful test doubles and rare degraded `state_ack_only.v2` fallbacks. Closure passed Django checks, focused core regressions and the complete suite through `scripts/ci_django_checks.sh`.
- Nutrition Solver Optimization V2 NSO00-NSO10 adds versioned Food Catalog capabilities, operational
  snapshots, multi-capability meal grammar, bounded combination planning, a deterministic CP-SAT
  backend, whole-day constraints, alternatives, shadow quality gates and controlled DailyPlan
  proposal activation. The heuristic path remains the default rollback until rollout evidence is accepted.
- Project Control, Clarity & Foresight PCF00-PCF10 aligns staging CI; the executable environment contract now formalizes 90
  environment variables, adds safe environment and OAuth diagnostics, exposes one
  executable status contract through CLI/Admin Operations/AI, validates the document
  registry, tracks explicit architectural transitions and maintains evidence-led
  product bets. The local closure passed the complete suite;
  deployed release identity and probe accuracy remain staging gates.
- Technical Debt Guardrails TDG00-TDG08 makes Django, MCP, browser, static analysis,
  dependency security, architecture boundaries, CSS debt and repository hygiene
  explicit quality surfaces. Admin Operations and AI runtime hotspots are decomposed
  behind stable facades, shared test builders reduce repeated setup and browser tests
  use deterministic environment-owned fixtures.
- Priority Technical Debt Closure TDG09-TDG14 separates the AI provider loop and
  tool-selection policy, reduces AI→`notas` imports from 22 to zero, makes the full
  authenticated browser suite deterministic in CI, removes duplicated staging CI,
  retires Nutrition Solver compatibility bridges and migrates `Profile.plan`
  capabilities reversibly into accounts-owned subscriptions.

## Planned near-term cycles

- No continuation of BA or PT is implied. New AI Assistant work should start from observed product evidence and a newly scoped cycle, rather than extending the global prompt or reopening a deterministic questionnaire.
- The current product bets and next experiments live in `PRODUCT_PORTFOLIO.md`; they are
  hypotheses to validate or reformulate, not a fixed feature sequence.

## Current work style

Use patches with narrow responsibility.

A good patch usually does one of these:

- document or update a plan;
- record an accepted decision;
- add or adjust a current contract;
- implement one technical slice;
- add a regression test for a known issue;
- clean one bounded area.

Avoid mixing documentation architecture, feature implementation, UI redesign, tests and unrelated cleanup in the same patch.

## Useful starting points

- `docs/00_current/AI_README.md`
- `docs/40_technical/operations/docs_information_architecture.md`
- `docs/00_current/architecture/layers.md`
- `docs/00_current/architecture/rules.md`
- `docs/40_technical/operations/testing_and_ci_policy.md`
- `docs/40_technical/qa/testing_hygiene_guide.md`
- `docs/10_active_cycles/README.md`
- `docs/20_decisions/README.md`
