# 0187 - Code quality consolidation after the August growth phase

Status: accepted
Date: 2026-08-31

## Context

My Scoope added a consumer mobile client, a broad mobile API, calendarized program
execution, catalog governance and shared UI contracts during August 2026. Existing
architecture tests and CI kept the product green, but the review found that several
quality signals no longer measured the highest-growth surfaces:

- Django coverage excluded `mobile_api`;
- coverage had no CI threshold;
- the workflow policy promised push validation on `staging`, while the workflow
  only triggered directly on `main` and `master`;
- mobile npm advisories were not audited in CI;
- mobile tests accumulated hundreds of assertions over source text and decorative
  JSX/CSS details;
- large API, schema, selector and test facades had no ownership or no-growth contract;
- type and complexity checks covered only a narrow baseline.

The repository remains functionally healthy. The problem is confidence quality and
future change cost, not a justification for a product rewrite.

## Decision

My Scoope adopts the CQC00-CQC08 quality-consolidation cycle with progressive,
executable ratchets:

1. CI directly validates pushes to `staging` and pull requests.
2. Django coverage includes `mobile_api`, runs with branch coverage in the complete
   CI job and enforces a conservative measured baseline.
3. Python and JavaScript dependency audits are independent quality surfaces.
   Vendor-blocked Expo findings use an exact reviewed allowlist that rejects new,
   changed or critical advisories.
4. Expo dependencies move only through SDK 57-compatible versions reported by Expo
   tooling; generic `npm audit fix` output is not an authority for SDK compatibility.
5. Mobile API public routes stay stable while domain ownership, facade budgets and
   incremental extractions make the implementation easier to navigate.
6. Mobile tests prefer behavior, accessibility and typed helpers. Source inspection
   is reserved for narrow architecture constraints and receives a declining budget.
7. Query-count, type and complexity checks are introduced as ratchets: existing debt
   is recorded, new debt fails, and improvements lower the baseline.

## Consequences

- CI becomes slightly more expensive but produces evidence for the code that changed
  most during the month.
- Known vendor advisories remain visible instead of being hidden or "fixed" through
  incompatible package downgrades.
- Refactors of mobile JSX stop requiring updates to large collections of decorative
  regex assertions.
- Large compatibility facades may remain temporarily, but their growth and ownership
  are explicit and tested.
- Coverage percentage is treated as one signal; domain, authorization and integration
  tests remain more important than maximizing a global number.
- The cycle does not authorize product behavior changes or a big-bang API rewrite.
