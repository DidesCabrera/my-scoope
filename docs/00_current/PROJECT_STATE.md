# Project State - My Scoope

Status: current
Last updated: 2026-07-16
Audience: developers and AI assistants

## What My Scoope is

My Scoope is a Django product for building, managing and evolving nutrition programs, food libraries, meals, daily plans, AI-assisted proposals and internal operational dashboards.

The product is evolving from a monolithic `notas` origin toward clearer app boundaries, with AI-assisted workflows, food catalog governance, nutrition solving, account plans/credits and internal admin tooling.

## Current product posture

My Scoope is past the first architecture-expansion phase. The current priority is operational confidence:

- staging must stay green;
- patches should be small and reviewable;
- tests should protect regressions and rules without blocking healthy UI evolution;
- docs should guide decisions without becoming a flat context dump;
- admin tooling should support operation, not just raw database editing.

## App responsibility map

| Area | Responsibility |
| --- | --- |
| `notas` | Legacy/product core for operational nutrition entities such as foods, meals, plans, programs and proposals while extraction continues. |
| `accounts` | User/account domain, onboarding ownership, commercial plans, subscriptions, credits and entitlements. |
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
- AI Assistant behavior should favor LLM freedom through typed tool contracts over prompt over-structuring or deterministic conversational guards.
- Behavioral alignment should direct the assistant through product purpose, current state, capabilities and boundaries rather than fixed dialogue scripts.
- User-visible credits are product/account concepts; provider tokens and costs are internal observability concepts.
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

## Documentation posture

`docs/` must be read as a hierarchy, not a flat folder.

- `docs/00_current/AI_README.md` is the AI entrypoint.
- `docs/00_current/` is the current source of implementation truth.
- `docs/20_decisions/` explains accepted rationale and history.
- `docs/10_active_cycles/` prepares cycles but does not override current contracts.
- `docs/90_archive/` is historical context only.

When a plan becomes real, durable outcomes should be promoted into `docs/00_current/` and decisions should be recorded in `docs/20_decisions/`.

## Recently closed baselines

- CI/staging stabilization and test hygiene baseline.
- Rate-limit dependency alignment for login/signup flows.
- Admin Operations V1 as an operational staff console.
- Admin Analytics as a strategic staff dashboard.
- Account plans/credits ownership moved toward `accounts`.
- Nutrition Solver separation baseline.
- Food Catalog launch-readiness cycle.
- AI Assistant activation/observability/credits guardrails.
- AI Assistant Client Memory & Profile Objects and LLM-native alignment cycle CM00-CM24. The final real-provider gate and targeted UX rerun passed automated and human review, consolidating native function calling, grounded state transitions and explicit cards.
- AI Assistant Behavioral Alignment BA00-BA07 and Post-Tool Follow-up Transport PT00-PT06 are closed. The accepted baseline covers domain anchoring, capability abstraction, ambiguous-intent restraint, goal-directed progression, response quality, exact provider call correlation, contract-faithful test doubles and rare degraded `state_ack_only.v2` fallbacks. Closure passed Django checks, 2 core regressions and the complete 1,446-test suite through `scripts/ci_django_checks.sh`.
- Nutrition Solver Optimization V2 NSO00-NSO10 adds versioned Food Catalog capabilities, operational
  snapshots, multi-capability meal grammar, bounded combination planning, a deterministic CP-SAT
  backend, whole-day constraints, alternatives, shadow quality gates and controlled DailyPlan
  proposal activation. The heuristic path remains the default rollback until rollout evidence is accepted.

## Planned near-term cycles

- No continuation of BA or PT is implied. New AI Assistant work should start from observed product evidence and a newly scoped cycle, rather than extending the global prompt or reopening a deterministic questionnaire.

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
