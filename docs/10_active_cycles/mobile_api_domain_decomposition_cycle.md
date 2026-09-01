# MADD00-MADD07 · Mobile API Domain Decomposition

Status: active
Owner: Mobile API / Architecture
Started: 2026-08-31
Decision: `docs/20_decisions/0189-mobile-api-domain-module-pattern.md`

## Purpose

Turn the explicit route-ownership map from CQC into physical, domain-owned modules
that make future maintenance easier without changing `/api/v1/`, OpenAPI identities,
authorization or product behavior.

## Baseline

- branch: `codex/mobile-api-domain-decomposition`, created from the completed CQC branch at `3dd6fb4`
- no parallel worktrees or uncommitted baseline changes
- `api.py`: 1,423 lines after the first extraction, down from 1,544
- `schemas.py`: 1,157 lines, down from 1,249
- `test_api_v1.py`: 1,793 lines, down from 2,055
- generated OpenAPI remains byte-for-byte current

## Invariants

1. Public paths, methods, status codes, envelopes and operation IDs remain unchanged.
2. Domain route modules own transport only and delegate product rules to existing services.
3. `api.py` remains the single composition root and exception-handler owner.
4. Compatibility imports remain available while callers migrate.
5. Tests move exactly once; inheritance must not duplicate discovery.
6. Every extraction lowers facade budgets and adds exact budgets for new modules.

## Stages

### MADD00 — Reference pattern: Comparisons — completed

- Extract seven routes to `mobile_api/routes/comparisons.py`.
- Extract independent schemas to `mobile_api/schema_domains/comparisons.py`.
- Move three endpoint contracts to `mobile_api/tests/test_comparisons_api.py`.
- Preserve all committed OpenAPI operation IDs explicitly.
- Add architecture checks for route discovery and pinned operation IDs.
- Validate 96 fast tests, quality checks, 1,811 complete Django tests and 77%
  branch coverage against the 75% minimum.

### MADD01 — Proposals — completed

- Move list/detail/review/apply routes, schemas and endpoint tests.
- Keep proposal queries and commands as the existing product authority.
- Preserve six operation IDs and the byte-identical OpenAPI contract.
- Reduce `api.py` to 1,316 lines, `schemas.py` to 1,061 and the legacy test suite to 1,663.

### MADD02 — Calendarization and Today — completed

- Group activation, lifecycle, day detail, Today, reviews, revisions, reminders,
  notification registration and weights in one vertical domain.
- Move 18 routes, 42 schemas and nine behavior tests out of the compatibility
  facades without duplicating test discovery.
- Preserve dated-snapshot and append-only evidence contracts, all operation IDs
  and the byte-identical generated OpenAPI contract.
- Reduce `api.py` to 1,116 lines, `schemas.py` to 792 and the legacy test suite
  to 1,240 while adding exact per-module debt budgets.

### MADD03 — Libraries and composition — completed

- Separate 15 collection/detail/action routes from 18 composition mutations and
  picker preview/commit flows in two explicit route modules.
- Move library and composition schemas to independent domains; comparison picker
  options now import the shared library-card contract instead of keeping it in the facade.
- Move 13 end-to-end behavior tests to `test_libraries_api.py`, preserving a
  readable create → compose → mutate → share/delete journey.
- Reduce `api.py` to 593 lines, `schemas.py` to 452 and the legacy test suite to
  457; selector extraction is deferred because its projection helpers remain a
  cohesive read boundary shared by these routes.

### MADD04 — Identity, account and billing — completed

- Put session/profile/onboarding/disclosures/deletion in `routes/identity.py` and
  entitlements/subscription evidence in `routes/billing.py`.
- Preserve independent account, billing and OAuth authorities and move their
  schemas and seven behavior tests to matching domain modules.
- Keep the cross-domain onboarding/weight and profile/entitlements assertions as
  explicit integration contracts rather than duplicating them.
- Reduce `api.py` to 447 lines, `schemas.py` to 354 and the legacy suite to 310.

### MADD05 — Assistant — planned

- Group chat, durable jobs and prepared-action routes without moving AI product rules into transport.

### MADD06 — Facade convergence — planned

- Reduce `api.py`, `schemas.py`, `selectors.py` and the legacy test suite to compatibility composition surfaces.
- Update imports only after all direct consumers have a domain home.

### MADD07 — Closure — planned

- Run all repository quality surfaces and branch coverage.
- Promote the final module map and record any remaining compatibility facade.

## Exit criteria

- Every `/api/v1/` route is registered by a domain router or an explicitly documented platform root.
- Domain schemas and tests can be found without searching the compatibility facades.
- OpenAPI remains unchanged unless a separate product decision intentionally changes it.
- Facade line budgets fall monotonically and all supported automated suites pass.
