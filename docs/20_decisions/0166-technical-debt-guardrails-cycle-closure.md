# Decision 0166: Technical Debt Guardrails cycle closure

Date: 2026-08-02
Status: completed
Cycle: TDG00-TDG08

## Context

The cycle began after substantial product growth, including a strategically larger
Food Catalog surface inside Admin Operations. The objective was to make repository
quality and architecture debt visible and reducible without shrinking that domain or
changing product behavior.

## Completed outcomes

- Django fast/full, MCP, browser and quality surfaces have declared dependencies,
  runnable scripts and CI ownership.
- The deployed dependency set has no vulnerability currently known to `pip-audit`.
- Fatal static correctness, production module cycles, cross-app dependencies,
  transitional AI/product adapters and Admin Operations HTTP concerns have executable
  ratchets.
- Admin Operations services, selectors and view models are domain-owned behind thin
  compatibility facades. Food Catalog remains its largest owned service surface by
  design.
- AI runtime configuration and provider parsing are separated, and tool schemas are
  grouped by capability behind the canonical registry.
- Small user/nutrition builders reduce repeated setup in selected high-volume tests.
- CSS debt cannot grow silently, and browser scenarios no longer commit database IDs,
  fixed sleeps or persisted authentication state.
- Eleven historical provider reports were moved from the repository root to the
  reviewed documentation archive.
- The obsolete deterministic-engine rollback transition was retired because the
  unified LLM decision is already enforced; the real AI/product adapter transition is
  registered instead.

## Closure evidence

- Django fast gate: 78 tests passed.
- Complete Django suite: 1,647 tests passed in 264.636 seconds in a clean updated
  dependency environment.
- MCP: 169 tests passed in its isolated environment.
- Browser: all 27 scenarios collect; the live anonymous Chromium smoke passed.
- Ruff fatal correctness rules: passed.
- Dependency audit: no known vulnerabilities found.
- Django checks and migration drift: clean.
- Document registry: valid with zero findings.
- Repository hygiene, CSS budget and browser contract: passed.

## Consequences

The repository has stronger feedback and clearer seams, but the ratchets are not a
claim that all historical style or coupling debt is gone. Future work should reduce
recorded ceilings and transitional allowlists in focused patches. It must not widen
them silently or use this closure to reduce Food Catalog's strategic and operational
role.
