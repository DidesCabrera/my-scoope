# My Scoope agent instructions

## Human Knowledge Center boundary

`admin_knowledge/` and `docs/00_current/features/admin_knowledge/` exist only to
present human-oriented explanatory material in the staff Knowledge Center.

- They are not a source of truth for product behavior, architecture, data
  contracts, permissions, or feature requirements.
- Do not use their wording to infer how the code works. Inspect implementation,
  migrations, tests, authoritative decisions, and the applicable current feature
  documentation instead.
- Do not update, synchronize, regenerate, or expand the Knowledge Center during a
  feature, refactor, bug fix, documentation cycle, or release by default.
- Change the Knowledge Center only when Felipe explicitly requests a Knowledge
  Center update in the current task.
- Product code must not import `admin_knowledge`. The only allowed integration
  points are Django installation/URL wiring and human navigation links.
- A feature is complete without a Knowledge Center change unless Felipe explicitly
  includes that app in scope.

These rules intentionally keep the human presentation layer from becoming a
second authority or influencing Codex's understanding of the codebase.

## Efficient validation policy

Engineering confidence must increase at every validation stage without paying
twice for the same evidence. Prefer the smallest check that can disprove the
current change, and reserve broad suites for integration boundaries.

- During product iteration, keep changes on a branch based on the current
  `staging`, use the local development client and Fast Refresh, and run focused
  tests, lint, or type checks for the affected area. Do not publish, open a PR,
  deploy, or wait for the complete CI suite merely to obtain visual feedback.
- For a visual mobile adjustment, use `scripts/ci_mobile_visual_check.sh` with
  only the directly related test file when one exists. It lints changed mobile
  files only and must not run the global typecheck or full mobile test set.
- Use `scripts/ci_mobile_iteration.sh` once when the user closes a mobile
  refinement stage. Use the complete `scripts/ci_mobile_checks.sh` gate once
  before integration.
- Obtain visual or functional approval before starting the integration cycle
  when the user is actively iterating on UI behavior.
- Before integration, run the relevant local gate once, then publish the exact
  tested commit. A direct push to `staging` is allowed when remote staging is
  genuinely needed; CI selects the `docs`, `mobile`, `staging-fast`, or `full`
  tier from the changed paths. Ordinary and mixed application work uses
  `staging-fast`; migrations, authentication, billing, dependencies, release
  configuration, CI infrastructure, and other explicitly critical paths use
  `full` even on `staging`.
- `main` is a strict boundary: integrate through a PR, require the repository
  checks, and always use the `full` tier. Do not repeat the same code suite
  after merging the already validated PR; use deployment checks for the
  post-merge evidence instead.
- Reuse successful validation only when the content is provably identical and
  the evidence comes from a trusted, required check. Commit messages, branch
  names, or human assertions are not proof. Missing or unverifiable evidence
  must fail safe by running the complete suite.
- Post-merge validation must add different evidence: deployment health,
  migrations, environment configuration, or a staging smoke test. Do not treat
  a second execution of identical code tests as deployment validation.
- Backend, schema, authentication, migration, dependency, or release changes
  may justify broader and earlier checks. State the concrete risk instead of
  defaulting every change to the slowest path.
- Report which validation tier is running and its expected cost. If a check is
  knowingly duplicated, explain why the earlier evidence cannot be reused.
- Do not run `ci_mobile_iteration.sh`, a global typecheck, or the complete mobile
  test set after each visual change. Reload the development client immediately
  after the focused check. Browser or staging workflows require a concrete need;
  existing staging-backed data is not a reason to repeat them.

The target feedback loop is seconds to a few minutes for local iteration and a
single complete CI cycle at integration. Efficiency never permits skipping the
one validation layer that owns the risk being introduced.
