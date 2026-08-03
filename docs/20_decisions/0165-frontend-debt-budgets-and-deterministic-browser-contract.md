# Decision 0165: frontend debt uses budgets and deterministic browser contracts

Date: 2026-08-02
Status: accepted
Cycle: TDG07

## Context

Large feature stylesheets and historical `!important` usage could grow without a
review signal. The browser suite depended on localhost URLs containing database IDs,
fixed sleeps and a locally persisted authentication state, so a tracked test was not
necessarily reproducible on another machine or in CI.

## Decision

- Split Admin Operations Food detail styles from the operational console base.
- Split Programs into base, chart and week-detail ownership files while preserving
  cascade order.
- Record reviewed line and `!important` ceilings for the ten largest/highest-debt
  project stylesheets and fail the fast gate on growth.
- Supply browser base URL, credentials and scenario object IDs through fixtures and
  environment variables.
- Log in afresh for authenticated contexts; do not read or write persisted browser
  state.
- Replace fixed waits with page readiness/ARIA-busy conditions and Playwright's
  locator auto-wait behavior.
- Run the anonymous homepage smoke in CI and retain seeded authenticated scenarios
  as an explicit local/staging surface.

## Consequences

- Admin Operations CSS is split from 2,235 lines into 1,579 base and 656 Food detail
  lines; Programs is split into 2,327 base, 2,603 chart and 374 week-detail lines.
- Existing debt is visible but does not require an unsafe all-at-once CSS rewrite.
- New fixed IDs, sleeps or persisted auth state fail an executable browser contract.
- All 27 scenarios collect in the clean declared environment and the anonymous
  Chromium smoke runs successfully against a live local server.
