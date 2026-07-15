# 0081 · Testing hygiene baseline

Date: 2026-07-08
Status: accepted
Cycle: TS01–TS02
Related docs:

```text
docs/40_technical/qa/testing_hygiene_guide.md
docs/40_technical/operations/testing_and_ci_policy.md
docs/20_decisions/0080-ci-stabilization-and-test-hygiene.md
```

## Context

The CI stabilization cycle left `staging` green in GitHub Actions. The main
lesson from that closure is that tests need an explicit operating structure.
They must help the product evolve, not become friction that preserves obsolete
behavior.

The recent local `django_ratelimit` import issue also reinforced an important
rule: local development should install the same declared dependencies as the
project, instead of adding silent fallbacks that make environments diverge.

## Decision

Adopt a test hygiene baseline for My Scoope.

Tests are grouped by intent:

```text
domain
integration
view/url/template smoke
regression
documentation
configuration
```

Functional patches should include the test that best matches the risk they
introduce. Bugfix patches for real CI, staging or local boot failures should add
a regression test when the failure can be represented automatically.

When no test is added, the patch notes should say why. Valid reasons include
documentation-only, CSS-only or copy-only changes.

## Accepted rules

1. Tests protect current accepted contracts, not old behavior.
2. A failing test is classified before product code is changed.
3. Domain tests are preferred for business rules.
4. Integration tests are used for cross-app product flows.
5. Regression tests are added for bugs that reached CI, staging or local boot.
6. Documentation tests should point to `docs/00_current/` and `docs/20_decisions/`.
7. Missing local dependencies should be solved with `pip install -r requirements.txt` when the dependency is already declared.

## Consequences

Positive:

- future patches have a clear test expectation;
- CI failures can be triaged without guessing;
- the suite can evolve with the product;
- staging remains a useful quality gate.

Tradeoffs:

- some feature patches will be slightly larger because tests and docs move with
  the contract;
- obsolete tests must be actively reviewed instead of blindly preserved;
- local environments must keep dependencies installed and aligned.

## TS02 executable baseline

TS02 adds a small regression namespace:

```text
core/tests/regressions/
scripts/test_regressions.sh
```

The first executable regression protects root URLConf import, Django resolver
loading, and rate-limited auth routes. This is intentionally small because the
full suite already covers many product flows; the baseline exists to catch boot
and configuration failures early.
