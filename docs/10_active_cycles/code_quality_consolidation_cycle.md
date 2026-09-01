# CQC00-CQC08 · Code Quality Consolidation Cycle

Status: completed
Owner: Architecture / Developer Experience
Started: 2026-08-31
Decision: `docs/20_decisions/0187-code-quality-consolidation.md`

## Purpose

Consolidate the quality of the code added during the August 2026 growth phase
without changing product behavior or reopening completed product cycles. The cycle
turns the external-style quality review into executable repository contracts for
CI, coverage, mobile dependency security, API modularity, test hygiene, query
performance and progressive static analysis.

## Baseline

- branch: `codex/code-quality-consolidation`, created from `staging` at `3a06d46`
- repository: clean, with no parallel worktrees
- August activity: 189 commits and 1,093 changed files since `9a69643`
- Django suite: 1,803 tests passing in 302.379 seconds locally
- Django branch coverage: 77%, but `mobile_api` is not included in the measured source set
- fast structural gate: 95 tests passing
- MCP suite: 169 tests passing
- mobile suite: 45 tests passing, with 583 source-regex assertions
- latest staging pull-request CI: green on Django/SQLite, PostgreSQL, MCP, browser, frontend, quality and mobile jobs
- dependency audit: Python and root npm clean; mobile npm reports 5 high and 3 moderate transitive advisories
- principal hotspots: `mobile_api/api.py`, `mobile_api/schemas.py`, `mobile_api/selectors.py`, `mobile_api/tests/test_api_v1.py` and fragile mobile source-contract tests

## Invariants

1. Public `/api/v1/` routes and the generated OpenAPI contract remain stable.
2. Product behavior, authorization, ownership, idempotency and response envelopes remain unchanged.
3. Expo packages stay on SDK 57-compatible versions selected through Expo tooling.
4. Existing debt is ratcheted before stricter whole-repository rules are enabled.
5. Coverage and query budgets protect risk-bearing code without encouraging low-value assertions.
6. UI tests protect behavior, accessibility and durable architecture seams, not decorative implementation details.
7. No database migration, provider activation, product redesign or Knowledge Center change belongs to this cycle.

## Patch sequence

### CQC00 — Baseline and cycle registration — completed

- Record review evidence, scope, invariants and exit criteria.
- Accept the quality-consolidation decision before implementation.

### CQC01 — CI and dependency-security alignment — completed

- Run the complete workflow directly on pushes to `staging` as documented.
- Upgrade Expo packages to the compatible SDK 57 patch set.
- Add npm audit ratchets for root and mobile dependencies.
- Fail on new advisories or any critical advisory while tracking vendor-blocked transitive findings explicitly.

### CQC02 — Measured coverage contract — completed

- Include `mobile_api` in Django coverage.
- Execute coverage in the complete Django CI job.
- Establish a conservative baseline threshold and publish missing-line evidence.

### CQC03 — Mobile API ownership map and no-growth budgets — completed

- Declare domain ownership for routes, schemas, selectors and tests.
- Add executable classification and size budgets for the current facade modules.
- Extract one cohesive route/schema surface behind the stable API facade to prove the seam.

### CQC04 — Mobile API test decomposition seam — completed

- Introduce a shared authenticated mobile API test base.
- Place architecture and performance contracts in focused domain modules.
- Freeze the legacy V1 suite at its reduced size so later product-domain moves are
  incremental, reviewable and cannot be replaced by duplicated inherited execution.

### CQC05 — Mobile test hygiene — completed

- Remove decorative source assertions from the largest mobile contract suites.
- Add behavioral tests for extracted state/contract helpers.
- Add a no-growth budget for remaining source-inspection assertions.

### CQC06 — Query regression budgets — completed

- Add bounded query-count tests for high-value mobile reads.
- Cover Today, active program and library surfaces without locking exact ORM implementation.

### CQC07 — Progressive static-analysis ratchets — completed

- Expand mypy to stable typed seams.
- Record current complex functions and reject new or worsening complexity debt.
- Record module-size hotspots and reject accidental growth outside approved extractions.

### CQC08 — Closure and current-contract promotion — completed

- Run the repository-supported fast, full, frontend, mobile, coverage and dependency checks locally; preserve PostgreSQL and physical-device checks as external CI/release gates.
- Promote durable testing/CI guidance into `docs/40_technical/` and current project state.
- Mark this cycle completed only with a clean worktree and documented remaining external/vendor gates.

## Exit criteria

- `staging` is an explicit push trigger for the complete CI workflow.
- Python, root npm and mobile npm audits are visible and ratcheted in CI.
- `mobile_api` contributes to a branch-aware coverage report with an enforced baseline.
- Mobile API ownership and hotspot budgets are executable.
- Mobile API tests have a shared authenticated base, focused architecture/query modules and an exact no-growth budget for the remaining legacy suite.
- Fragile source-regex assertions are materially reduced and cannot grow silently.
- Critical mobile read paths have query budgets.
- New Python complexity debt is rejected while existing hotspots cannot worsen.
- OpenAPI, migrations, document registry and all supported automated suites pass.

## External and vendor gates

- Transitive Expo/React Native advisories without a compatible SDK 57 fix remain an explicit dependency budget, not a silent pass.
- Physical iOS behavior remains covered by the existing device/TestFlight gates; this repository cycle does not replace them.

## Delivered outcome

- `staging` is an explicit full-workflow push target.
- The complete Django job measures branch coverage, includes `mobile_api` and fails below 75%.
- Expo SDK 57 packages are aligned to the compatible patch set; root and mobile npm audits are enforced through exact reviewed budgets.
- `/api/v1/` keeps its public contract while common response/error handling lives in `mobile_api/api_support.py` and every declared route has a domain owner.
- Six backend/mobile hotspots have exact no-growth line budgets.
- Mobile source-inspection debt fell from 91 to 83 source reads and from 583 to 525 regex assertions; the comparator now has behavioral state tests.
- Today, active-program and library-program reads have bounded query-count tests.
- Mypy covers five stable modules instead of two, and 14 pre-existing complex functions are frozen with no new exceptions permitted.

## Closure evidence

- fast gate: 96 tests passed
- complete Django suite: 1,809 tests passed in 292.500 seconds
- branch coverage including `mobile_api`: 78% against a 75% minimum
- mobile: lint, typecheck, 46 tests and export of 44 static routes passed
- Python dependency audit: no known vulnerabilities
- npm audit: root clean; mobile 7 reviewed transitive findings (4 high, 3 moderate, 0 critical)
- OpenAPI, migrations, repository hygiene and document registry: passed

## Remaining controlled debt

- `mobile_api/tests/test_api_v1.py` remains a compatibility-heavy legacy suite. New architecture and performance tests no longer enter it, and its exact line budget requires future extraction to be monotonic.
- Seven Expo/Metro transitive advisories remain until the SDK 57 dependency graph offers compatible fixes; any new, changed or critical finding fails CI.
- PostgreSQL CI, signed iOS behavior and staging/TestFlight validation remain external gates and were not simulated locally.
