# 0188 - Code quality consolidation closure

Status: completed
Date: 2026-08-31

## Context

Decision 0187 opened a bounded consolidation cycle after the August product-growth
phase. The repository was functionally green, but coverage, dependency security,
mobile test hygiene and structural debt controls did not fully observe the new
consumer mobile surfaces.

## Decision

CQC00-CQC08 is complete at the repository boundary. The durable contract is:

1. pushes to `staging` run the complete GitHub workflow;
2. branch coverage includes `mobile_api` and cannot fall below 75%;
3. Python, root npm and mobile npm audits are mandatory, with an exact temporary
   budget only for SDK 57-compatible vendor transitives;
4. mobile API routes have executable domain ownership and compatibility facades have
   exact no-growth size limits;
5. new mobile tests prefer behavioral helpers, while remaining source inspection has
   a declining budget;
6. critical mobile reads have bounded query counts;
7. typed seams expand progressively and no new or worsened Python complexity
   exception is accepted.

The remaining monolithic mobile API regression file is not declared remediated. Its
shared authenticated fixture, focused architecture/performance modules and exact
no-growth ceiling form the safe seam for incremental domain extraction without a
high-risk rewrite or duplicated test discovery.

## Evidence

- 96 fast tests and 1,809 complete Django tests passed.
- Branch coverage is 78%, including `mobile_api`, against a 75% enforced minimum.
- Mobile lint, typecheck, 46 tests and a 44-route static export passed.
- Python and root npm audits are clean.
- Mobile npm has 7 exact reviewed transitives: 4 high, 3 moderate, 0 critical.
- OpenAPI drift, migration drift, repository hygiene and documentation registry checks passed.

## Consequences

- Quality regressions now fail at the surface where they are introduced instead of
  relying on a periodic manual review.
- Existing debt remains visible and cannot silently grow; improvements must lower
  their budgets.
- Compatible Expo/Metro fixes should remove audit entries as they become available.
- PostgreSQL CI, staging and physical iOS/TestFlight remain external validation gates.
