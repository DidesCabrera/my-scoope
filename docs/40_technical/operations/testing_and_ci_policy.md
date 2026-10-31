# Testing & CI Policy

Status: active
Last updated: 2026-10-31
Applies to: local iteration, `staging`, pull requests, GitHub Actions and deployment evidence

## Purpose

Tests in My Scoope exist to increase confidence and development speed. They should
protect current product contracts, domain rules and integration boundaries. They
should not preserve outdated behavior after a documented decision changes the
architecture.

## Operating modes

Choose the smallest mode that owns the requested outcome. Moving to a later mode
is an explicit boundary, not an automatic consequence of making a local change.

| Mode | Source preparation | Validation | Completion evidence |
| --- | --- | --- | --- |
| Consult or audit | Current checkout is sufficient for read-only work | None unless a claim needs an executable check | Evidence-backed answer |
| Iterate locally | Fresh `origin/staging` in an isolated task worktree | Focused check for the changed risk | Local behavior or reviewable patch |
| Integrate to staging | Refresh and compare with current `origin/staging` | Changed-path CI tier | Exact remote commit and required CI summary |
| Promote to production | Green staging content through a PR to `main` | Always `full` before merge | Deployment, migration, environment or smoke evidence |

Do not fetch, create a branch, open a worktree, publish, or run a broad suite for a
read-only consultation merely because those actions are required by later modes.

## Branch and release policy

```text
local work -> staging -> GitHub Actions -> staging web QA -> PR to main -> production
```

`staging` is the integration branch. Technical edits begin from the current remote
staging commit in an isolated task branch. Staging may receive patches and
corrective commits, but it must return to green before it becomes the source of a
production pull request.

`main` should only receive code from a green `staging` branch.

### Mandatory production workflow

Production work must follow this order:

```text
1. Make and review the change locally from the current `origin/staging` base.
2. Run the focused local evidence and commit only the intended files.
3. Integrate the exact validated content into `staging` and require its selected CI tier.
4. Open a pull request from `staging` to `main`.
5. Merge the pull request to `main`.
6. Verify the deployed production site or confirm the deployment blocker.
```

Do not push feature fixes directly to `main`, and do not treat a staging PR as
complete when the user asked for production visibility. The task is not complete
until the production path has either visibly updated or the remaining deployment
blocker has been identified.

The production boundary is strict; the iteration boundary is intentionally light.
Do not open a PR, deploy, or wait for broad CI merely to obtain local visual or
functional feedback.

## Validation tiers

GitHub Actions is the external quality gate because it runs in a clean environment,
not on the developer machine.

The executable classifier is `scripts/ci_change_scope.sh`; the workflow enforcement
is `.github/workflows/django-ci.yml`. Documentation describes the intent, while
those files determine the actual selected tier.

| Tier | Typical scope | Required evidence |
| --- | --- | --- |
| `docs` | Markdown and canonical documentation only | Repository growth/debt preflight plus static correctness and dependency audit |
| `mobile` | Mobile-only application changes | Static/dependency quality plus complete mobile contract and bundle gate |
| `staging-fast` | Ordinary backend, frontend or mixed application work | Fast Django, MCP, browser smoke, frontend, mobile and quality gates |
| `full` | Migrations, auth, billing, dependencies, release/CI configuration and other critical paths | `staging-fast` plus complete Django and PostgreSQL suites |

`main` always selects `full`, regardless of changed paths. Staging uses the tier
selected from the actual diff. A full green run is therefore required before
merging to `main`, but ordinary staging work is not automatically a full-suite run.

## Validation progression and evidence reuse

1. During iteration, use the smallest focused check that can disprove the current
   change. For visual mobile work, use `scripts/ci_mobile_visual_check.sh` with the
   directly related test when one exists and reload through Fast Refresh.
2. When a mobile refinement stage closes, run `scripts/ci_mobile_iteration.sh`
   once. Run `scripts/ci_mobile_checks.sh` once before integration.
3. Before staging integration, run the relevant local gate once, fetch again and
   publish the exact tested content. CI then owns the changed-path tier.
4. Reuse successful evidence only when the content is provably identical and the
   result comes from a trusted required check. Branch names, commit messages and
   assertions are not proof.
5. If the base or content changes, rerun only the evidence invalidated by that
   change. If identity cannot be established, fail safe with the complete tier.
6. After merge, validate the deployed boundary: health, migrations, environment,
   provider configuration, staging smoke, physical device or store behavior as
   applicable. Repeating an identical code suite is not deployment evidence.

State the chosen tier and its expected cost. Explain any deliberate duplicate run
by naming the content change or evidence gap that prevented reuse.

## Test categories

### Domain tests

Protect business rules and invariants.

Examples:

- a wallet cannot silently lose credits;
- a proposal cannot be applied twice;
- a private plan cannot be used by another user;
- a solver contract returns validated structures.

These tests are high value and should rarely be weakened.

### Integration tests

Protect important flows across apps.

Examples:

- AI Assistant generates a reviewable proposal;
- proposal application creates user-owned nutrition entities;
- credit charging records observable usage;
- Admin Operations mutates state with audit events.

These tests may need fixture updates when app boundaries move, but they should keep
protecting the product flow.

### UI/HTML tests

Protect meaningful user-facing affordances.

Use stable checks whenever possible. Prefer data attributes or structural contracts
over decorative copy when the exact text is not the product contract.

### Documentation tests

Protect source-of-truth documentation.

They should read from:

```text
docs/00_current/
docs/20_decisions/
```

They should not depend on `docs/90_archive/` unless the test explicitly validates
historical migration context.

### Configuration tests

Protect the difference between production safety and CI determinism.

Examples:

- onboarding gates;
- rate limits;
- AI credit limits;
- feature flags;
- environment-driven settings.

These tests must make the intended environment explicit.

## Test hygiene rules

Detailed guidance lives in `docs/40_technical/qa/testing_hygiene_guide.md`.

### 1. A failing test must be classified first

Do not immediately change product code. First decide whether the failure is:

```text
product regression
obsolete expectation
fragile assertion
configuration mismatch
fixture/setup issue
```

### 2. Tests must follow current contracts

When a patch changes a product contract, the patch must update related tests in the
same cycle.

Example:

```text
Old contract: approved/final proposal is directly apply-ready.
Current contract: applicable proposal becomes applied through an explicit command.
```

The test should protect the current contract.

### 3. CI settings must not weaken production settings

CI may override settings to make tests deterministic, but those overrides must be
explicit and scoped to CI or tests.

Examples:

```text
NUTRITION_ONBOARDING_GATE_ENABLED=false for broad historical tests.
RATE_LIMIT_AI_ASSISTANT_TURN_USER=10000/h for full CI suite determinism.
```

Production must keep the protective defaults.

For a whole-project local boundary, the authoritative command is:

```bash
scripts/ci_django_checks.sh
```

This aggregate command resolves the project interpreter without requiring an
activated virtual environment and runs both Django quality layers:

```text
scripts/ci_fast_checks.sh          structural/configuration/architecture feedback
scripts/ci_django_full_suite.sh    complete Django regression suite
```

Other repository test surfaces have independent dependency and execution contracts:

```text
scripts/test_mcp.sh                MCP contract and protocol suite
scripts/test_e2e.sh                browser suite against an already running server
```

MCP and the anonymous browser smoke are required GitHub Actions jobs. Seeded browser
scenarios remain local/staging evidence and receive base URL, credentials and object
IDs through the environment; they never persist auth state. Browser dependencies
live in `e2e/requirements.txt`, never runtime requirements.

Do not classify redirects from a raw `python manage.py test` invocation as CI regressions until the repository's explicit test environment has been applied. The script preserves production defaults in production while making the historical suite deterministic.

### 4. Avoid invisible dependencies on test order

A test should not pass only when another test ran first. Shared state through cache,
rate limits, global settings or singleton services must be reset or overridden.

### 5. Prefer factories and helpers for common setup

Repeated manual setup increases fragility. Common test data should move toward
helpers/factories, especially for:

```text
users
profiles
wallets
plans
AI proposals
foods/meals/daily plans
```

## Executable quality ratchets

The complete Django job must run branch-aware coverage through
`scripts/coverage_django.sh`. The measured source set includes `mobile_api`, and the
repository minimum is 75%. Raising the threshold requires a measured green baseline;
lowering it requires an explicit accepted decision.

Dependency safety has independent contracts:

```text
Python runtime dependencies   pip-audit, no known vulnerabilities
root npm dependencies         exact audit budget, currently clean
mobile npm dependencies       exact reviewed SDK-compatible transitive budget
```

An audit budget is not a vulnerability waiver. It records the exact vendor-blocked
finding so a new package, severity change or critical advisory fails CI. Expo package
compatibility is determined with Expo SDK tooling before changing the budget.

Progressive debt controls live under `config/` and are checked by the CI scripts:

- backend/mobile hotspot line ceilings are no-growth limits;
- remaining mobile source reads and regex assertions have declining ceilings;
- Python functions above complexity 15 are an exact reviewed set;
- query budgets protect Today, active program and library reads from hidden N+1 growth;
- mypy expands through stable typed seams instead of enabling a repository-wide flag without remediation.

When a refactor improves one of these measurements, lower its committed budget in
the same patch. Do not reuse the recovered allowance for unrelated growth.

## Patch checklist

Every functional patch should either add/update an appropriate test or explicitly
state why no test is needed, such as docs-only, CSS-only or copy-only changes.

Before pushing a patch to `staging`:

```text
[ ] Does this patch change a product contract?
[ ] Were related tests updated in the same patch?
[ ] If no test was added, is the reason explicit in the patch notes?
[ ] Are new tests protecting domain behavior rather than copy or implementation detail?
[ ] Are CI/test-only settings explicit?
[ ] Did local focused tests pass?
[ ] Did GitHub Actions pass after push?
```

## Pull request checklist

Before opening or reopening a PR to `main`:

```text
[ ] staging is green in GitHub Actions.
[ ] staging has been manually checked in the web environment when UI/auth flows changed.
[ ] docs/00_current or docs/20_decisions were updated when the patch changed a stable contract.
[ ] no `.orig`, `.rej`, generated files or local artifacts are committed.
```

## Principle

```text
Tests are a living quality contract.
They must help My Scoope evolve safely, not force the product to preserve obsolete
behavior.
```
