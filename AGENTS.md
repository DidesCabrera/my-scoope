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

## AI team organization and memory

My Scoope's AI roles, reporting relationships, lifecycle states, and shared
operating model live under `.codex/team/`. The discoverable role instructions
live under `.codex/skills/`.

- Read `.codex/team/README.md` when a task concerns the composition, delegation,
  evaluation, or evolution of the AI team.
- Use `.codex/team/capability-registry.yaml` as the organizational inventory. A
  role's `SKILL.md` remains authoritative for that role's behavior and limits.
- Store durable area and initiative context in `.codex/team/memory/` only when it
  helps later work. Link to product sources of truth instead of copying them.
- Team memory is not authoritative for product behavior, architecture, data
  contracts, permissions, accounting treatment, or accepted business decisions.
- Never store secrets, credentials, private customer data, health data, raw
  financial account data, or unnecessary personal information in team memory.
- Creating a role does not grant it permission to mutate external systems. The
  current user request and the role's authority boundaries still control writes.

## Fresh task checkout boundary

Use the smallest operating mode that owns the requested outcome:

- **Consult or audit:** read-only work may use the current checkout. It does not
  require a fetch, branch, worktree, or test suite unless a specific claim needs an
  executable check.
- **Iterate locally:** code or documentation edits start from a freshly fetched
  `origin/staging` in an isolated `codex/<task>` worktree and use focused checks.
- **Integrate to staging:** refresh the remote again, validate the changed-path
  tier, and publish the exact tested content.
- **Promote to production:** use a staging-to-main PR, the full required gate, and
  deployment evidence after merge.

A local branch named `staging` or an already-open checkout is not proof of current
code. Use the `fresh-task-checkout` workflow for edit tasks.

- Do not reset, clean, switch, pull, or rebase a dirty or unrelated checkout to
  prepare new work.
- Use `origin/main` only when the task is explicitly scoped to the production line
  or the user names that base.
- If fetching fails, report that freshness is unverified. If `origin/main` has
  commits absent from `origin/staging`, report the divergence before ordinary work
  begins rather than silently reconciling it.
- Record the selected base ref and full commit SHA before editing. Fetch and compare
  again before integration because `origin/staging` may advance during the task.

## Efficient validation policy

`docs/40_technical/operations/testing_and_ci_policy.md` is the canonical workflow
and validation policy. `.github/workflows/django-ci.yml` and
`scripts/ci_change_scope.sh` are its executable enforcement.

- During iteration, run the smallest focused check that can disprove the change.
  Visual mobile work uses the focused visual check and Fast Refresh; complete
  mobile checks run once at the integration boundary.
- At staging integration, CI selects `docs`, `mobile`, `staging-fast`, or `full`
  from changed paths. Critical paths use `full`; ordinary application work uses
  `staging-fast`.
- `main` always uses `full`. Reuse trusted evidence only for provably identical
  content and add deployment, migration, environment, provider, or device
  evidence after merge instead of repeating the same code suite.
- State the selected tier and expected cost. If validation is duplicated, explain
  which changed content or missing evidence invalidated the earlier result.

Efficiency never permits skipping the one validation layer that owns the risk.
